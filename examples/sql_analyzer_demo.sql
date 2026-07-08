-- =============================================
--  SQL Analyzer 演示：慢查询优化实战
-- =============================================

-- 场景：从交易记录中统计"每只股票近30天日均成交量 > 100万"的活跃股，
--       并关联持仓信息，生成活跃股持仓报表。
--
-- 假设数据量：
--   trades 表 500万行
--   holdings 表 200万行
--   stocks 表 5000行


-- ========== 原始 SQL（写得很随意） ==========

SELECT *
FROM trades t, holdings h, stocks s
WHERE t.stock_id = h.stock_id
  AND t.stock_id = s.id
  AND t.trade_date >= '2026-06-01'
  AND t.volume > 0
  AND h.quantity > 0
  AND s.status = 'listed'
GROUP BY t.stock_id, s.code, s.name, h.account_id, h.quantity, h.cost_price
HAVING AVG(t.volume) > 1000000
ORDER BY AVG(t.volume) DESC;


-- ========== 优化后 SQL ==========

-- 先用子查询预筛选活跃股，再 JOIN 持仓与股票信息

WITH active_stocks AS (
    SELECT
        stock_id,
        AVG(volume) AS avg_volume
    FROM trades
    WHERE trade_date >= '2026-06-01'
      AND volume > 0
    GROUP BY stock_id
    HAVING AVG(volume) > 1000000
)
SELECT
    s.code,
    s.name,
    h.account_id,
    h.quantity,
    h.cost_price,
    a.avg_volume
FROM active_stocks a
INNER JOIN stocks s    ON s.id = a.stock_id AND s.status = 'listed'
INNER JOIN holdings h  ON h.stock_id = a.stock_id AND h.quantity > 0
ORDER BY a.avg_volume DESC;


-- ========== 建议索引 ==========

-- 1. trades 表：覆盖"时间范围 + volume 过滤 + stock_id 聚合"的查询
CREATE INDEX idx_trades_date_vol_stock ON trades (trade_date, volume, stock_id);

-- 2. holdings 表：覆盖按 stock_id + quantity 过滤的 JOIN
CREATE INDEX idx_holdings_stock_qty  ON holdings (stock_id, quantity);

-- 3. stocks 表：覆盖主键 + status 过滤的 JOIN
CREATE INDEX idx_stocks_id_status     ON stocks (id, status);


-- ========== EXPLAIN 对比（PostgreSQL 示例） ==========

-- 优化前：
EXPLAIN ANALYZE
SELECT *
FROM trades t, holdings h, stocks s
WHERE t.stock_id = h.stock_id
  AND t.stock_id = s.id
  AND t.trade_date >= '2026-06-01'
  AND t.volume > 0
  AND h.quantity > 0
  AND s.status = 'listed'
GROUP BY t.stock_id, s.code, s.name, h.account_id, h.quantity, h.cost_price
HAVING AVG(t.volume) > 1000000
ORDER BY AVG(t.volume) DESC;

-- 优化后：
EXPLAIN ANALYZE
WITH active_stocks AS (
    SELECT stock_id, AVG(volume) AS avg_volume
    FROM trades
    WHERE trade_date >= '2026-06-01' AND volume > 0
    GROUP BY stock_id
    HAVING AVG(volume) > 1000000
)
SELECT s.code, s.name, h.account_id, h.quantity, h.cost_price, a.avg_volume
FROM active_stocks a
INNER JOIN stocks s   ON s.id = a.stock_id AND s.status = 'listed'
INNER JOIN holdings h ON h.stock_id = a.stock_id AND h.quantity > 0
ORDER BY a.avg_volume DESC;
