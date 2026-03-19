import { Layout, Menu, Typography } from "antd";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { HistoryPage } from "./pages/HistoryPage";
import { SearchPage } from "./pages/SearchPage";
import { SettingsPage } from "./pages/SettingsPage";

const { Header, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: "/", label: <Link to="/">检索</Link> },
  { key: "/history", label: <Link to="/history">历史</Link> },
  { key: "/settings", label: <Link to="/settings">设置</Link> }
];

export default function App() {
  const location = useLocation();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header className="pn-header">
        <div className="pn-header-inner">
          <Title level={4} style={{ margin: 0, color: "#f9f9f7" }}>
            PaperNote
          </Title>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            className="pn-menu"
          />
        </div>
      </Header>
      <Content className="pn-content">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Content>
    </Layout>
  );
}
