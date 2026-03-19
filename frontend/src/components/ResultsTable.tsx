import { Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { PaperResult } from "../types";

const { Paragraph, Text, Link } = Typography;

interface ResultsTableProps {
  rows: PaperResult[];
  loading?: boolean;
}

export function ResultsTable({ rows, loading }: ResultsTableProps) {
  const sourceFilters = Array.from(new Set(rows.map((item) => item.source)))
    .filter(Boolean)
    .map((source) => ({ text: source, value: source }));

  const yearFilters = Array.from(new Set(rows.map((item) => item.year).filter(Boolean)))
    .sort((a, b) => Number(b) - Number(a))
    .map((year) => ({ text: String(year), value: year as number }));

  const tagFilters = Array.from(new Set(rows.flatMap((item) => item.tags))).map((tag) => ({
    text: tag,
    value: tag
  }));

  const columns: ColumnsType<PaperResult> = [
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      width: 280,
      render: (_value, record) => (
        <div>
          {record.url ? (
            <Link href={record.url} target="_blank">
              {record.title}
            </Link>
          ) : (
            <Text strong>{record.title}</Text>
          )}
          {record.pdf_url ? (
            <div>
              <Link href={record.pdf_url} target="_blank">
                PDF
              </Link>
            </div>
          ) : null}
        </div>
      )
    },
    {
      title: "作者",
      dataIndex: "authors",
      key: "authors",
      width: 180,
      render: (authors: string[]) => (
        <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}>
          {authors.join(", ")}
        </Paragraph>
      )
    },
    {
      title: "年份",
      dataIndex: "year",
      key: "year",
      width: 80,
      filters: yearFilters,
      onFilter: (value, record) => record.year === value,
      sorter: (a, b) => (a.year ?? 0) - (b.year ?? 0)
    },
    {
      title: "日期",
      dataIndex: "published_date",
      key: "published_date",
      width: 120,
      sorter: (a, b) => (a.published_date ?? "").localeCompare(b.published_date ?? "")
    },
    {
      title: "期刊/会议",
      dataIndex: "venue",
      key: "venue",
      width: 160
    },
    {
      title: "来源",
      dataIndex: "source",
      key: "source",
      width: 110,
      filters: sourceFilters,
      onFilter: (value, record) => record.source === value
    },
    {
      title: "DOI",
      dataIndex: "doi",
      key: "doi",
      width: 180,
      render: (value: string | undefined) => value || "-"
    },
    {
      title: "摘要",
      dataIndex: "abstract",
      key: "abstract",
      width: 320,
      render: (abstract: string) => (
        <Paragraph ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}>{abstract || "-"}</Paragraph>
      )
    },
    {
      title: "主题标签",
      dataIndex: "tags",
      key: "tags",
      width: 180,
      filters: tagFilters,
      onFilter: (value, record) => record.tags.includes(String(value)),
      render: (tags: string[]) => (
        <>
          {tags.length ? tags.map((tag) => <Tag key={tag}>{tag}</Tag>) : <Text type="secondary">-</Text>}
        </>
      )
    },
    {
      title: "相关性",
      dataIndex: "relevance_score",
      key: "relevance_score",
      width: 110,
      sorter: (a, b) => a.relevance_score - b.relevance_score
    },
    {
      title: "一句话总结",
      dataIndex: "summary",
      key: "summary",
      width: 260,
      render: (summary: string) => (
        <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}>{summary || "-"}</Paragraph>
      )
    },
    {
      title: "匹配理由",
      dataIndex: "reason",
      key: "reason",
      width: 260,
      render: (reason: string) => (
        <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: "展开" }}>{reason || "-"}</Paragraph>
      )
    }
  ];

  return (
    <Table<PaperResult>
      rowKey="id"
      loading={loading}
      columns={columns}
      dataSource={rows}
      pagination={{ pageSize: 10, showSizeChanger: true }}
      scroll={{ x: 2200 }}
    />
  );
}
