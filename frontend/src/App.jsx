import { useEffect, useMemo, useState } from "react";
import {
  createEntry,
  exportData,
  fetchEntries,
  fetchReview,
  fetchStats,
  getSentenceAudioBlob,
  getWordAudioUrl,
  importData,
} from "./api";

const TABS = ["复习", "词条管理", "导入导出", "统计趋势"];
const REVIEW_PAGE_SIZE = 8;
const MANAGE_PAGE_SIZE = 10;

function TrendChart({ title, data }) {
  const maxValue = Math.max(1, ...(data || []).map((d) => d.count));

  return (
    <div className="card">
      <h3>{title}</h3>
      {!data?.length && <p>暂无数据</p>}
      {!!data?.length && (
        <div className="trend-wrap">
          {data.map((point) => (
            <div key={point.label} className="trend-item" title={`${point.label}: ${point.count}`}>
              <div className="trend-bar-bg">
                <div
                  className="trend-bar"
                  style={{ height: `${Math.max(8, (point.count / maxValue) * 100)}%` }}
                />
              </div>
              <span className="trend-count">{point.count}</span>
              <span className="trend-label">{point.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("复习");
  const [period, setPeriod] = useState("weekly");
  const [review, setReview] = useState({ items: [] });
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState(null);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [expandedMap, setExpandedMap] = useState({});
  const [reviewPage, setReviewPage] = useState(1);
  const [managePage, setManagePage] = useState(1);

  const [entryForm, setEntryForm] = useState({ word: "", sentence: "" });

  const periodLabel = useMemo(() => {
    const map = { weekly: "近一周", monthly: "近一月", yearly: "近一年" };
    return map[period] || "近一周";
  }, [period]);

  const filteredEntries = useMemo(() => {
    const k = search.trim().toLowerCase();
    if (!k) return entries;
    return entries.filter((x) => `${x.word} ${x.sentence} ${x.meaning || ""}`.toLowerCase().includes(k));
  }, [entries, search]);

  const reviewTotalPages = Math.max(1, Math.ceil((review.items?.length || 0) / REVIEW_PAGE_SIZE));
  const reviewPageItems = useMemo(() => {
    const start = (reviewPage - 1) * REVIEW_PAGE_SIZE;
    return (review.items || []).slice(start, start + REVIEW_PAGE_SIZE);
  }, [review.items, reviewPage]);

  const manageTotalPages = Math.max(1, Math.ceil(filteredEntries.length / MANAGE_PAGE_SIZE));
  const managePageItems = useMemo(() => {
    const start = (managePage - 1) * MANAGE_PAGE_SIZE;
    return filteredEntries.slice(start, start + MANAGE_PAGE_SIZE);
  }, [filteredEntries, managePage]);

  async function loadReview() {
    try {
      const data = await fetchReview(period, 50);
      setReview(data);
      setReviewPage(1);
      setMessage(`已加载 ${data.items.length} 条复习内容。`);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "加载复习数据失败。\n请检查后端服务。 ");
    }
  }

  async function loadEntries() {
    try {
      const data = await fetchEntries();
      setEntries(data);
      setManagePage(1);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "加载词条失败。\n请检查接口。 ");
    }
  }

  async function loadStats() {
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "加载统计失败。\n请稍后重试。 ");
    }
  }

  useEffect(() => {
    loadReview();
  }, [period]);

  useEffect(() => {
    if (tab === "词条管理") {
      loadEntries();
    }
    if (tab === "统计趋势") {
      loadStats();
    }
  }, [tab]);

  useEffect(() => {
    loadEntries();
    loadStats();
  }, []);

  async function playWordAudio(word) {
    try {
      const url = await getWordAudioUrl(word);
      const audio = new Audio(url);
      await audio.play();
    } catch {
      setMessage("单词发音播放失败。 ");
    }
  }

  async function playSentenceAudio(text, entryId = null) {
    try {
      const blob = await getSentenceAudioBlob(text, entryId);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      await audio.play();
      audio.onended = () => URL.revokeObjectURL(url);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "例句语音生成失败。 ");
    }
  }

  async function handleCreateEntry(e) {
    e.preventDefault();
    try {
      await createEntry(entryForm);
      setEntryForm({ word: "", sentence: "" });
      setMessage("词条已添加，单词信息已自动补全。 ");
      loadEntries();
      loadReview();
      loadStats();
    } catch (err) {
      setMessage(err?.response?.data?.detail || "添加词条失败。 ");
    }
  }

  async function handleExport() {
    try {
      const data = await exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "enstudy-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("导出成功。 ");
    } catch {
      setMessage("导出失败。 ");
    }
  }

  async function handleImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importData(file);
      const skipped = result.skipped_items || 0;
      const sampleSkipped = (result.skipped_words || []).slice(0, 8).join("、");
      setMessage(
        skipped
          ? `导入完成：新增 ${result.imported_items || 0} 条，跳过 ${skipped} 条（重复单词）。${sampleSkipped ? ` 示例: ${sampleSkipped}` : ""}`
          : `导入完成，共新增 ${result.imported_items || 0} 条。`
      );
      loadEntries();
      loadReview();
      loadStats();
    } catch (err) {
      setMessage(err?.response?.data?.detail || "导入失败。 ");
    }
  }

  function toggleDetail(entryId) {
    setExpandedMap((prev) => ({ ...prev, [entryId]: !prev[entryId] }));
  }

  function renderPagination(page, totalPages, onChange) {
    return (
      <div className="pager">
        <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1}>
          上一页
        </button>
        <span>
          第 {page} / {totalPages} 页
        </span>
        <button onClick={() => onChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>
          下一页
        </button>
      </div>
    );
  }

  function renderEntryDetail(w) {
    const isExpanded = !!expandedMap[w.id];
    const posItems = w.part_of_speech_items?.length ? w.part_of_speech_items : (w.part_of_speech ? [w.part_of_speech] : []);
    const meaningItems = w.meaning_items?.length ? w.meaning_items : (w.meaning ? [w.meaning] : []);

    return (
      <>
        <p>音标: {w.phonetic || "-"}</p>
        <p>词性: {posItems[0] || "-"}</p>
        <p>释义: {meaningItems[0] || "暂无释义"}</p>
        {isExpanded && (
          <div className="entry-all-details">
            <p>全部词性: {posItems.length ? posItems.join(" / ") : "-"}</p>
            <p>全部释义:</p>
            <ol>
              {meaningItems.map((m, index) => (
                <li key={`${w.id}-meaning-${index}`}>{m}</li>
              ))}
            </ol>
          </div>
        )}
        <button className="link-btn" onClick={() => toggleDetail(w.id)}>
          {isExpanded ? "收起" : "查看全部信息"}
        </button>
      </>
    );
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>EnStudy</h1>
        <p>你的英语学习词条库，自动补全发音、词性和释义。</p>
      </header>

      <nav className="tabs">
        {TABS.map((item) => (
          <button
            key={item}
            className={item === tab ? "tab active" : "tab"}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </nav>

      {message && <div className="message">{message}</div>}

      {tab === "复习" && (
        <section className="panel">
          <div className="row">
            <h2>{periodLabel}复习</h2>
            <div className="controls">
              <select value={period} onChange={(e) => setPeriod(e.target.value)}>
                <option value="weekly">按周</option>
                <option value="monthly">按月</option>
                <option value="yearly">按年</option>
              </select>
            </div>
          </div>

          <div className="card">
            <div className="card-header-row">
              <h3>复习词条</h3>
              <span className="chip">共 {review.items.length} 条</span>
            </div>
            {reviewPageItems.map((w) => (
              <div key={w.id} className="item">
                <div>
                  <strong>{w.word}</strong>
                  {renderEntryDetail(w)}
                  <p>例句: {w.sentence}</p>
                </div>
                <div className="controls">
                  <button onClick={() => playWordAudio(w.word)}>单词发音</button>
                  <button onClick={() => playSentenceAudio(w.sentence, w.id)}>例句朗读</button>
                </div>
              </div>
            ))}
            {renderPagination(reviewPage, reviewTotalPages, setReviewPage)}
          </div>
        </section>
      )}

      {tab === "词条管理" && (
        <section className="panel">
          <form className="card" onSubmit={handleCreateEntry}>
            <div className="card-header-row form-title-row">
              <h3>新增词条</h3>
              <button type="submit" className="title-action-btn">保存词条</button>
            </div>
            <p>只需填写单词和例句，其余字段由 Free Dictionary API 自动补全。</p>
            <div className="grid two">
              <input
                placeholder="单词，例如: resilient"
                value={entryForm.word}
                onChange={(e) => setEntryForm((v) => ({ ...v, word: e.target.value }))}
                required
              />
              <input
                placeholder="例句，例如: She is resilient in difficult times."
                value={entryForm.sentence}
                onChange={(e) => setEntryForm((v) => ({ ...v, sentence: e.target.value }))}
                required
              />
            </div>
          </form>

          <div className="card">
            <div className="row">
              <h3>词条列表</h3>
              <div className="manage-tools">
                <input
                  className="search"
                  placeholder="搜索单词/例句/释义"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setManagePage(1);
                  }}
                />
                <span className="chip">命中 {filteredEntries.length} 条</span>
              </div>
            </div>
            {managePageItems.map((w) => (
              <div key={w.id} className="item">
                <div>
                  <strong>{w.word}</strong>
                  {renderEntryDetail(w)}
                  <p>例句: {w.sentence}</p>
                </div>
                <div className="controls">
                  <button onClick={() => playWordAudio(w.word)}>单词发音</button>
                  <button onClick={() => playSentenceAudio(w.sentence, w.id)}>例句朗读</button>
                </div>
              </div>
            ))}
            {renderPagination(managePage, manageTotalPages, setManagePage)}
          </div>
        </section>
      )}

      {tab === "导入导出" && (
        <section className="panel">
          <div className="card">
            <h3>导入 / 导出</h3>
            <div className="row">
              <button onClick={handleExport}>导出 JSON</button>
              <label className="upload">
                导入 JSON/CSV
                <input type="file" accept=".json,.csv" onChange={handleImport} />
              </label>
            </div>
            <p>JSON 格式: {`{"items":[{"word":"resilient","sentence":"..."}]}`}</p>
            <p>CSV 表头: word,sentence</p>
          </div>
        </section>
      )}

      {tab === "统计趋势" && (
        <section className="panel">
          <div className="grid four">
            <div className="stat">
              <h3>{stats?.total_items ?? 0}</h3>
              <p>总词条</p>
            </div>
            <div className="stat">
              <h3>{stats?.items_last_7_days ?? 0}</h3>
              <p>近 7 天</p>
            </div>
            <div className="stat">
              <h3>{stats?.items_last_30_days ?? 0}</h3>
              <p>近 30 天</p>
            </div>
            <div className="stat">
              <h3>{stats?.items_last_365_days ?? 0}</h3>
              <p>近 365 天</p>
            </div>
          </div>

          <div className="grid two">
            <TrendChart title="按周趋势" data={stats?.weekly_trend || []} />
            <TrendChart title="按月趋势" data={stats?.monthly_trend || []} />
          </div>
        </section>
      )}
    </div>
  );
}
