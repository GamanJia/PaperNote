import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Typography,
  message
} from "antd";
import { getSettings, saveSettings, testLLM } from "../api/papernote";
import type { AppSettings, LLMProviderType } from "../types";

const { Title } = Typography;

interface SettingsFormValues {
  provider_type: LLMProviderType;
  base_url?: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  enabled_sources: string[];
  default_export_format: "csv" | "xlsx" | "markdown";
}

export function SettingsPage() {
  const [form] = Form.useForm<SettingsFormValues>();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [apiKeyForTest, setApiKeyForTest] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const settings = await getSettings();
      form.setFieldsValue({
        provider_type: settings.default_model.provider_type,
        base_url: settings.default_model.base_url ?? undefined,
        model_name: settings.default_model.model_name,
        temperature: settings.default_model.temperature,
        max_tokens: settings.default_model.max_tokens,
        enabled_sources: settings.enabled_sources,
        default_export_format: settings.default_export_format
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载设置失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onSave = async (values: SettingsFormValues) => {
    const payload: AppSettings = {
      default_model: {
        provider_type: values.provider_type,
        base_url: values.base_url || null,
        model_name: values.model_name,
        temperature: values.temperature,
        max_tokens: values.max_tokens,
        api_key: null
      },
      enabled_sources: values.enabled_sources,
      default_export_format: values.default_export_format
    };
    try {
      await saveSettings(payload);
      message.success("设置已保存");
    } catch (error) {
      message.error(error instanceof Error ? error.message : "保存失败");
    }
  };

  const onTest = async () => {
    const values = form.getFieldsValue();
    setTesting(true);
    try {
      const response = await testLLM({
        provider_type: values.provider_type,
        base_url: values.base_url || null,
        model_name: values.model_name,
        temperature: values.temperature,
        max_tokens: values.max_tokens,
        api_key: apiKeyForTest || null
      });
      message.success(response.detail);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "连接测试失败");
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card loading={loading}>
      <Title level={4} style={{ marginTop: 0 }}>
        默认设置
      </Title>
      <Form layout="vertical" form={form} onFinish={onSave}>
        <Form.Item label="默认 Provider" name="provider_type">
          <Select
            options={[
              { label: "OpenAI-compatible", value: "openai-compatible" },
              { label: "Ollama", value: "ollama" }
            ]}
          />
        </Form.Item>
        <Form.Item label="Base URL" name="base_url">
          <Input />
        </Form.Item>
        <Form.Item label="Model Name" name="model_name">
          <Input />
        </Form.Item>
        <Form.Item label="Temperature" name="temperature">
          <InputNumber min={0} max={2} step={0.1} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="Max Tokens" name="max_tokens">
          <InputNumber min={64} max={8192} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="数据源开关" name="enabled_sources">
          <Checkbox.Group
            options={[
              { label: "OpenAlex", value: "openalex" },
              { label: "arXiv", value: "arxiv" }
            ]}
          />
        </Form.Item>
        <Form.Item label="默认导出格式" name="default_export_format">
          <Select
            options={[
              { label: "CSV", value: "csv" },
              { label: "XLSX", value: "xlsx" },
              { label: "Markdown", value: "markdown" }
            ]}
          />
        </Form.Item>

        <Space direction="vertical" style={{ width: "100%" }}>
          <Form.Item label="API Key（仅用于连接测试，不会保存）">
            <Input.Password value={apiKeyForTest} onChange={(e) => setApiKeyForTest(e.target.value)} />
          </Form.Item>
          <Space>
            <Button htmlType="submit" type="primary">
              保存设置
            </Button>
            <Button loading={testing} onClick={onTest}>
              测试模型连接
            </Button>
          </Space>
        </Space>
      </Form>
    </Card>
  );
}
