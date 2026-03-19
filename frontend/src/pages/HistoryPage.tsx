import { useEffect, useState } from "react";
import {
  Button,
  Drawer,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { deleteHistory, getHistory, listHistory, rerunHistory } from "../api/papernote";
import { ResultsTable } from "../components/ResultsTable";
import type { HistoryDetail, HistorySummary } from "../types";

const { Text } = Typography;

export function HistoryPage() {
  const [rows, setRows] = useState<HistorySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await listHistory();
      setRows(response);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载历史失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadHistory();
  }, []);

  const onView = async (searchId: string) => {
    try {
      const record = await getHistory(searchId);
      setDetail(record);
      setDrawerOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "加载详情失败");
    }
  };

  const onDelete = async (searchId: string) => {
    try {
      await deleteHistory(searchId);
      message.success("删除成功");
      await loadHistory();
      if (detail?.id === searchId) {
        setDrawerOpen(false);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "删除失败");
    }
  };

  const onRerun = async (searchId: string) => {
    try {
      const response = await rerunHistory(searchId);
      message.success(`重跑完成，得到 ${response.results.length} 条结果`);
      await loadHistory();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "重跑失败");
    }
  };

  const columns: ColumnsType<HistorySummary> = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 300,
      render: (value: string) => <Text code>{value}</Text>
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title"
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm:ss")
    },
    {
      title: "候选",
      dataIndex: "total_candidates",
      key: "total_candidates",
      width: 80
    },
    {
      title: "结果",
      dataIndex: "final_results",
      key: "final_results",
      width: 80
    },
    {
      title: "操作",
      key: "action",
      width: 220,
      render: (_value, record) => (
        <Space>
          <Button size="small" onClick={() => onView(record.id)}>
            查看
          </Button>
          <Button size="small" onClick={() => onRerun(record.id)}>
            重跑
          </Button>
          <Popconfirm title="确认删除该记录?" onConfirm={() => onDelete(record.id)}>
            <Button size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <>
      <Table<HistorySummary>
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 12 }}
      />

      <Drawer
        title={detail?.title || "历史详情"}
        placement="right"
        width={1100}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        {detail ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Text>时间：{dayjs(detail.created_at).format("YYYY-MM-DD HH:mm:ss")}</Text>
            <Text>
              主题：
              <Tag color="blue">{detail.parsed_query.topic || "-"}</Tag>
            </Text>
            <Text>关键词：{detail.parsed_query.keywords.join(", ") || "-"}</Text>
            <Text>扩展关键词：{detail.parsed_query.expanded_keywords.join(", ") || "-"}</Text>
            <ResultsTable rows={detail.results} />
          </Space>
        ) : null}
      </Drawer>
    </>
  );
}
