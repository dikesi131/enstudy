import { useEffect, useMemo, useState } from "react";
import {
  completeReview,
  createEntry,
  exportData,
  fetchEntries,
  fetchReview,
  fetchStats,
  getSentenceAudioBlob,
  getWordAudioUrl,
  importData,
} from "./api";

const TABS = ["复习", "词条管理", "导入导出", "统计趋势", "复习曲线"];
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

function ReviewLineChart({ title, data }) {
  const points = data || [];
  const maxValue = Math.max(1, ...points.map((d) => d.count || 0));

  if (!points.length) {
    return (
      <div className="card">
        <h3>{title}</h3>
        <p>暂无数据</p>
      </div>
    );
  }

  const width = 640;
  const height = 220;
  const left = 34;
  const right = 16;
  const top = 12;
  const bottom = 34;
  const innerW = width - left - right;
  const innerH = height - top - bottom;
  const stepX = points.length > 1 ? innerW / (points.length - 1) : 0;

  const chartPoints = points.map((item, idx) => {
    const x = left + stepX * idx;
    const y = top + innerH - (Math.max(0, item.count || 0) / maxValue) * innerH;
    return { x, y, label: item.label, count: item.count || 0 };
  });

  const polyline = chartPoints.map((p) => `${p.x},${p.y}`).join(" ");
  const labelStep = Math.max(1, Math.ceil(points.length / 6));

  return (
    <div className="card">
      <h3>{title}</h3>
      <svg className="review-line-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line x1={left} y1={top} x2={left} y2={height - bottom} className="review-axis" />
        <line x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} className="review-axis" />
        <polyline points={polyline} className="review-line" />
        {chartPoints.map((p, idx) => (
          <g key={`${title}-point-${idx}`}>
            <circle cx={p.x} cy={p.y} r="3.2" className="review-dot" />
            {idx % labelStep === 0 || idx === chartPoints.length - 1 ? (
              <text x={p.x} y={height - 10} textAnchor="middle" className="review-x-label">
                {p.label}
              </text>
            ) : null}
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("复习");
  const [managePeriod, setManagePeriod] = useState("weekly");
  const [review, setReview] = useState({ items: [] });
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState(null);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [expandedMap, setExpandedMap] = useState({});
  const [reviewPage, setReviewPage] = useState(1);
  const [managePage, setManagePage] = useState(1);
  const [reviewJumpPage, setReviewJumpPage] = useState("");
  const [manageJumpPage, setManageJumpPage] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResultCount, setImportResultCount] = useState(null);
  const [reviewCurveGranularity, setReviewCurveGranularity] = useState("daily");

  const [entryForm, setEntryForm] = useState({ word: "", sentence: "" });

  const managePeriodLabel = useMemo(() => {
    const map = { weekly: "近一周", monthly: "近一月", yearly: "近一年" };
    return map[managePeriod] || "近一周";
  }, [managePeriod]);

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

  const reviewCurveConfig = useMemo(() => {
    const map = {
      daily: { title: "复习曲线（每天）", data: stats?.review_daily_trend || [] },
      weekly: { title: "复习曲线（每周）", data: stats?.review_weekly_trend || [] },
      monthly: { title: "复习曲线（每月）", data: stats?.review_monthly_trend || [] },
      yearly: { title: "复习曲线（每年）", data: stats?.review_yearly_trend || [] },
    };
    return map[reviewCurveGranularity] || map.daily;
  }, [reviewCurveGranularity, stats]);

  async function loadReview() {
    try {
      const data = await fetchReview(50);
      setReview(data);
      setReviewPage(1);
      setMessage(`艾宾浩斯复习：今日应复习 ${data.items.length} 条词卡。`);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "加载复习数据失败。\n请检查后端服务。 ");
    }
  }

  async function handleCompleteReview(entryId, outcome) {
    const outcomeLabelMap = {
      remembered: "记住",
      fuzzy: "模糊",
      forgot: "忘记",
    };
    try {
      await completeReview(entryId, outcome);
      const label = outcomeLabelMap[outcome] || "模糊";
      setMessage(`已记录掌握程度：${label}，并按艾宾浩斯曲线更新下次复习。 `);
      loadReview();
    } catch (err) {
      setMessage(err?.response?.data?.detail || "标记复习失败。 ");
    }
  }

  async function loadEntries() {
    try {
      const data = await fetchEntries(managePeriod);
      setEntries(data);
      setManagePage(1);
      setManageJumpPage("");
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
  }, []);

  useEffect(() => {
    loadEntries();
  }, [managePeriod]);

  useEffect(() => {
    if (tab === "词条管理") {
      loadEntries();
    }
    if (tab === "统计趋势" || tab === "复习曲线") {
      loadStats();
    }
  }, [tab]);

  useEffect(() => {
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
    setIsImporting(true);
    setImportProgress(0);
    try {
      const result = await importData(file, (progressEvent) => {
        const total = progressEvent?.total || 0;
        if (!total) return;
        const percent = Math.max(0, Math.min(100, Math.round((progressEvent.loaded / total) * 100)));
        setImportProgress(percent);
      });
      const importedCount = result.imported_items || 0;
      const skipped = result.skipped_items || 0;
      const sampleSkipped = (result.skipped_words || []).slice(0, 8).join("、");
      const profileFailed = result.profile_failed_items || 0;
      const sampleProfileFailed = (result.profile_failed_words || []).slice(0, 8).join("、");
      setMessage(
        skipped
          ? `导入完成：新增 ${importedCount} 条，跳过 ${skipped} 条（重复单词）。${sampleSkipped ? ` 示例: ${sampleSkipped}` : ""}${profileFailed ? ` 其中 ${profileFailed} 条词典信息获取失败，已仅导入单词和例句。${sampleProfileFailed ? ` 示例: ${sampleProfileFailed}` : ""}` : ""}`
          : `导入完成，共新增 ${importedCount} 条。${profileFailed ? ` 其中 ${profileFailed} 条词典信息获取失败，已仅导入单词和例句。${sampleProfileFailed ? ` 示例: ${sampleProfileFailed}` : ""}` : ""}`
      );
      setImportResultCount(importedCount);
      loadEntries();
      loadReview();
      loadStats();
    } catch (err) {
      setMessage(err?.response?.data?.detail || "导入失败。 ");
    } finally {
      setImportProgress(100);
      setTimeout(() => {
        setIsImporting(false);
        setImportProgress(0);
      }, 300);
      e.target.value = "";
    }
  }

  function toggleDetail(entryId) {
    setExpandedMap((prev) => ({ ...prev, [entryId]: !prev[entryId] }));
  }

  function renderPagination(page, totalPages, onChange, jumpPageValue, setJumpPageValue) {
    function jumpToPage() {
      const next = Number.parseInt(jumpPageValue, 10);
      if (!Number.isInteger(next)) return;
      onChange(Math.max(1, Math.min(totalPages, next)));
      setJumpPageValue("");
    }

    return (
      <div className="pager">
        <button onClick={() => onChange(1)} disabled={page <= 1}>
          首页
        </button>
        <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1}>
          上一页
        </button>
        <span>
          第 {page} / {totalPages} 页
        </span>
        <button onClick={() => onChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages}>
          下一页
        </button>
        <button onClick={() => onChange(totalPages)} disabled={page >= totalPages}>
          尾页
        </button>
        <input
          className="pager-jump-input"
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          placeholder="页码"
          value={jumpPageValue}
          onChange={(e) => setJumpPageValue(e.target.value.replace(/\D/g, ""))}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              jumpToPage();
            }
          }}
        />
        <button onClick={jumpToPage} disabled={!jumpPageValue.trim()}>
          跳转
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

      {isImporting && (
        <div className="import-mask" role="status" aria-live="polite">
          <div className="import-dialog">
            <h3>正在导入中</h3>
            <p>文件上传和词典补全需要一些时间，请稍候。</p>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${importProgress}%` }} />
            </div>
            <p className="progress-text">上传进度: {importProgress}%</p>
          </div>
        </div>
      )}

      {importResultCount !== null && (
        <div className="import-mask" role="dialog" aria-modal="true" aria-live="polite">
          <div className="import-dialog import-result-dialog">
            <h3>导入成功</h3>
            <p>本次共导入 {importResultCount} 条词条。</p>
            <div className="import-result-actions">
              <button onClick={() => setImportResultCount(null)}>知道了</button>
            </div>
          </div>
        </div>
      )}

      {tab === "复习" && (
        <section className="panel">
          <div className="row">
            <h2>艾宾浩斯应复习词卡（今日）</h2>
          </div>

          <div className="card">
            <div className="card-header-row">
              <h3>应复习词条</h3>
              <span className="chip">待复习 {review.items.length} 条</span>
            </div>
            {!reviewPageItems.length && <p>当前范围内暂无应复习词条。</p>}
            {reviewPageItems.map((w) => (
              <div key={w.id} className="item">
                <div>
                  <strong>{w.word}</strong>
                  <p>
                    复习阶段: 第 {Number(w.review_stage || 0) + 1} 轮 {w.is_due ? "（已到期）" : "（即将到期）"}
                  </p>
                  <p>下次复习时间: {w.next_review_at ? new Date(w.next_review_at).toLocaleString() : "-"}</p>
                  {renderEntryDetail(w)}
                  <p>例句: {w.sentence}</p>
                </div>
                <div className="controls">
                  <button onClick={() => playWordAudio(w.word)}>单词发音</button>
                  <button onClick={() => playSentenceAudio(w.sentence, w.id)}>例句朗读</button>
                  <button className="review-rate remembered" onClick={() => handleCompleteReview(w.id, "remembered")}>记住</button>
                  <button className="review-rate fuzzy" onClick={() => handleCompleteReview(w.id, "fuzzy")}>模糊</button>
                  <button className="review-rate forgot" onClick={() => handleCompleteReview(w.id, "forgot")}>忘记</button>
                </div>
              </div>
            ))}
            {renderPagination(reviewPage, reviewTotalPages, setReviewPage, reviewJumpPage, setReviewJumpPage)}
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
                <select
                  value={managePeriod}
                  onChange={(e) => setManagePeriod(e.target.value)}
                  aria-label="词条时间范围"
                >
                  <option value="weekly">本周</option>
                  <option value="monthly">本月</option>
                  <option value="yearly">本年</option>
                </select>
                <input
                  className="search"
                  placeholder={`搜索${managePeriodLabel}单词/例句/释义`}
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setManagePage(1);
                  }}
                />
                <span className="chip">{managePeriodLabel}命中 {filteredEntries.length} 条</span>
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
            {renderPagination(managePage, manageTotalPages, setManagePage, manageJumpPage, setManageJumpPage)}
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

      {tab === "复习曲线" && (
        <section className="panel">
          <div className="row">
            <h2>复习曲线</h2>
            <div className="controls">
              <select
                value={reviewCurveGranularity}
                onChange={(e) => setReviewCurveGranularity(e.target.value)}
                aria-label="复习曲线时间粒度"
              >
                <option value="daily">每天</option>
                <option value="weekly">每周</option>
                <option value="monthly">每月</option>
                <option value="yearly">每年</option>
              </select>
            </div>
          </div>
          <div className="review-line-single">
            <ReviewLineChart title={reviewCurveConfig.title} data={reviewCurveConfig.data} />
          </div>
        </section>
      )}
    </div>
  );
}
