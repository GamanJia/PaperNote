import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Divider,
  Form,
  Input,
  InputNumber,
  message,
  Progress,
  Row,
  Select,
  Space,
  Switch,
  Tag,
  Typography
} from "antd";
import type { Dayjs } from "dayjs";
import { buildApiUrl } from "../api/client";
import {
  exportResults,
  getSettings,
  listSources,
  listVenueOptions,
  runSearch
} from "../api/papernote";
import { ResultsTable } from "../components/ResultsTable";
import type {
  AppSettings,
  LLMConfig,
  SearchRequest,
  SearchResponse,
  SourceItem,
  VenueOptions
} from "../types";

const { TextArea } = Input;
const { Title, Text } = Typography;

interface SearchFormValues {
  journals: string[];
  conferences: string[];
  date_start?: Dayjs;
  date_end?: Dayjs;
  keywords: string[];
  research_direction?: string;
  paper_description?: string;
  max_results: number;
  enable_llm_filter: boolean;
  enable_keyword_expansion: boolean;
  sort_by: "relevance" | "date_desc" | "year_desc";
  sources: string[];
  llm_concurrency: number;
  cache_ttl_minutes: number;
}

const BACKEND_DEFAULT_MODEL_FALLBACK: LLMConfig = {
  provider_type: "openai-compatible",
  base_url: null,
  model_name: "",
  api_key: null,
  temperature: 0.2,
  max_tokens: 1024
};

function toPayload(values: SearchFormValues, model: LLMConfig): SearchRequest {
  return {
    filters: {
      journals: values.journals ?? [],
      conferences: values.conferences ?? [],
      year_start: null,
      year_end: null,
      date_start: values.date_start ? values.date_start.format("YYYY-MM-DD") : null,
      date_end: values.date_end ? values.date_end.format("YYYY-MM-DD") : null
    },
    query: {
      keywords: values.keywords ?? [],
      research_direction: values.research_direction || null,
      paper_description: values.paper_description || null
    },
    params: {
      max_results: values.max_results,
      enable_llm_filter: values.enable_llm_filter,
      enable_keyword_expansion: values.enable_keyword_expansion,
      sort_by: values.sort_by,
      sources: values.sources ?? [],
      llm_concurrency: values.llm_concurrency,
      cache_ttl_minutes: values.cache_ttl_minutes
    },
    model
  };
}

export function SearchPage() {
  const [form] = Form.useForm<SearchFormValues>();
  const [loading, setLoading] = useState(false);
  const [searchProgress, setSearchProgress] = useState(0);
  const [estimatedSeconds, setEstimatedSeconds] = useState(0);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [modelConfig, setModelConfig] = useState<LLMConfig | null>(null);
  const [venueOptions, setVenueOptions] = useState<VenueOptions>({
    conferences: [],
    journals: []
  });
  const [venueOptionsLoading, setVenueOptionsLoading] = useState(false);
  const progressTimerRef = useRef<number | null>(null);

  const stopProgressTicker = () => {
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  };

  const estimateSearchSeconds = (values: SearchFormValues): number => {
    let estimate = 12;
    if (values.sources?.includes("openalex")) estimate += 10;
    if (values.sources?.includes("arxiv")) estimate += 4;
    if (values.enable_keyword_expansion) estimate += 5;
    if (values.enable_llm_filter) estimate += 18;
    if ((values.max_results ?? 40) > 40) estimate += 6;
    return Math.min(90, Math.max(8, estimate));
  };

  const applySettings = (settings: AppSettings) => {
    const nextModel: LLMConfig = {
      ...settings.default_model,
      api_key: null
    };
    setModelConfig(nextModel);
    form.setFieldsValue({
      sources: settings.enabled_sources.length ? settings.enabled_sources : ["openalex", "arxiv"]
    });
    return nextModel;
  };

  const loadSettings = async (notifyOnError: boolean): Promise<LLMConfig | null> => {
    try {
      const settings = await getSettings();
      return applySettings(settings);
    } catch (error) {
      if (notifyOnError) {
        message.error(error instanceof Error ? error.message : "加载默认模型配置失败");
      }
      return null;
    }
  };

  useEffect(() => {
    listSources()
      .then((sourceData) => {
        setSources(sourceData);
      })
      .catch((error: Error) => message.error(error.message));

    setVenueOptionsLoading(true);
    listVenueOptions({ limit: 300 })
      .then((venueData) => {
        setVenueOptions(venueData);
      })
      .catch((error: Error) => message.error(error.message))
      .finally(() => {
        setVenueOptionsLoading(false);
      });

    loadSettings(false).then((loaded) => {
      if (!loaded) {
        message.warning("默认模型配置加载失败，可稍后重试或检查后端服务。");
      }
    });

    return () => {
      stopProgressTicker();
    };
  }, []);

  const onSearch = async (values: SearchFormValues) => {
    let activeModel = modelConfig;
    if (!activeModel) {
      activeModel = await loadSettings(true);
    }
    if (!activeModel) {
      message.warning("默认模型配置未加载，已回退为后端默认配置继续检索。");
    }
    const requestModel = activeModel ?? BACKEND_DEFAULT_MODEL_FALLBACK;
    if (values.date_start && values.date_end && values.date_start.isSame(values.date_end, "day")) {
      message.warning("当前日期范围仅 1 天，可能导致 0 结果。建议扩大到至少 1 个月。");
    }
    const estimate = estimateSearchSeconds(values);
    setEstimatedSeconds(estimate);
    setSearchProgress(2);
    stopProgressTicker();
    const startedAt = Date.now();
    progressTimerRef.current = window.setInterval(() => {
      const elapsed = (Date.now() - startedAt) / 1000;
      const ratio = Math.min(1, elapsed / estimate);
      const next = Math.min(95, Math.round(2 + ratio * 93));
      setSearchProgress((prev) => (next > prev ? next : prev));
    }, 350);
    setLoading(true);
    try {
      const response = await runSearch(toPayload(values, requestModel));
      setSearchResult(response);
      setSearchProgress(100);
      message.success(`检索完成，返回 ${response.results.length} 篇论文`);
      if (response.stats.failed_sources.length) {
        message.warning(
          `部分数据源未完成：${response.stats.failed_sources.join(", ")}。已返回可用结果。`
        );
      }
      if (response.stats.fallback_date_relaxed) {
        message.info("当前查询触发了日期自动放宽（按年份边界）以避免误伤检索结果。");
      }
      if (response.results.length === 0 && response.stats.venue_filtered_out > 0) {
        message.warning(
          "当前开启了会议/期刊严格匹配，相关候选已因 venue 不一致被过滤。若需找 arXiv 预印本，请清空会议/期刊后重试。"
        );
      }
    } catch (error) {
      setSearchProgress(100);
      message.error(error instanceof Error ? error.message : "检索失败");
    } finally {
      stopProgressTicker();
      setLoading(false);
    }
  };

  const onExport = async (format: "csv" | "xlsx" | "markdown") => {
    if (!searchResult) {
      message.warning("请先执行检索");
      return;
    }
    try {
      const res = await exportResults({
        search_id: searchResult.search_id,
        format
      });
      window.open(buildApiUrl(res.download_url), "_blank", "noopener,noreferrer");
      message.success(`已导出 ${res.file_name}`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "导出失败");
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card>
        <Title level={3} style={{ marginTop: 0 }}>
          PaperNote 检索
        </Title>
        <Form<SearchFormValues>
          form={form}
          layout="vertical"
          onFinish={onSearch}
          initialValues={{
            journals: [],
            conferences: [],
            keywords: [],
            max_results: 40,
            enable_llm_filter: true,
            enable_keyword_expansion: true,
            sort_by: "relevance",
            sources: ["openalex", "arxiv"],
            llm_concurrency: 4,
            cache_ttl_minutes: 120
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="journals" label="期刊（可多选）">
                <Select
                  mode="multiple"
                  showSearch
                  allowClear
                  maxTagCount="responsive"
                  loading={venueOptionsLoading}
                  placeholder="从数据源可检索期刊中选择"
                  optionFilterProp="label"
                  options={venueOptions.journals.map((item) => ({ label: item, value: item }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="conferences" label="会议（可多选）">
                <Select
                  mode="multiple"
                  showSearch
                  allowClear
                  maxTagCount="responsive"
                  loading={venueOptionsLoading}
                  placeholder="从数据源可检索会议中选择"
                  optionFilterProp="label"
                  options={venueOptions.conferences.map((item) => ({ label: item, value: item }))}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="date_start" label="日期开始">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="date_end" label="日期结束">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="keywords" label="关键词（多个）">
            <Select mode="tags" placeholder="输入关键词后回车" />
          </Form.Item>
          <Form.Item name="research_direction" label="研究方向">
            <Input placeholder="例如：多模态大模型推理" />
          </Form.Item>
          <Form.Item name="paper_description" label="文章内容描述">
            <TextArea rows={4} placeholder="输入你关心的问题、方法、任务描述" />
          </Form.Item>

          <Divider />

          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="max_results" label="最大返回数量">
                <InputNumber min={1} max={200} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="sort_by" label="排序方式">
                <Select
                  options={[
                    { label: "相关性", value: "relevance" },
                    { label: "日期降序", value: "date_desc" },
                    { label: "年份降序", value: "year_desc" }
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="llm_concurrency" label="LLM 并发上限">
                <InputNumber min={1} max={20} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="cache_ttl_minutes" label="缓存分钟">
                <InputNumber min={1} max={1440} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="sources" label="数据源">
                <Select
                  mode="multiple"
                  options={sources.map((item) => ({ label: item.name, value: item.id }))}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="enable_llm_filter" label="启用 LLM 语义筛选" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="enable_keyword_expansion"
                label="启用关键词扩展"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>

          <Divider />

          <Alert
            type="info"
            showIcon
            message="模型配置来自“设置页”（或 .env 默认值），检索页不再重复填写。"
          />
          {!venueOptionsLoading &&
          venueOptions.conferences.length === 0 &&
          venueOptions.journals.length === 0 ? (
            <Alert
              type="warning"
              showIcon
              message="会议/期刊可选项加载失败，当前仅能在不指定 venue 的情况下检索。"
            />
          ) : null}

          {loading ? (
            <Space direction="vertical" style={{ width: "100%" }} size={4}>
              <Text type="secondary">预计等待约 {estimatedSeconds} 秒（动态估算）</Text>
              <Progress percent={searchProgress} status="active" size="small" />
            </Space>
          ) : null}

          <Button type="primary" htmlType="submit" loading={loading}>
            开始检索
          </Button>
        </Form>
      </Card>

      {searchResult ? (
        <Card>
          <Space direction="vertical" style={{ width: "100%" }} size={14}>
            <Title level={4} style={{ margin: 0 }}>
              解析后的查询条件
            </Title>
            <Text>主题：{searchResult.parsed_query.topic || "-"}</Text>
            <Space wrap>
              {searchResult.parsed_query.keywords.map((item) => (
                <Tag key={`kw-${item}`}>{item}</Tag>
              ))}
              {searchResult.parsed_query.expanded_keywords.map((item) => (
                <Tag color="blue" key={`exp-${item}`}>
                  {item}
                </Tag>
              ))}
            </Space>

            <Text type="secondary">
              候选论文 {searchResult.total_candidates} 篇，最终 {searchResult.results.length} 篇，耗时{" "}
              {searchResult.stats.duration_ms} ms
            </Text>

            <Space>
              <Button onClick={() => onExport("csv")}>导出 CSV</Button>
              <Button onClick={() => onExport("xlsx")}>导出 XLSX</Button>
              <Button onClick={() => onExport("markdown")}>导出 Markdown</Button>
            </Space>

            <ResultsTable rows={searchResult.results} loading={loading} />
          </Space>
        </Card>
      ) : null}
    </Space>
  );
}
