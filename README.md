# DVOL 中转（交易机访问不到 Deribit 时的数据通道）

**问题**：阿里云交易机对 Deribit / Binance / OKX / Bybit 全部连接超时；`api.github.com` 稳定可达，`raw.githubusercontent.com` 偶发 `ConnectionResetError(10054)`。
`pool_cycle.fetch_dvol()` 失败后只能用缓存，缓存超过 `data.max_iv_age_days`（4 天）后 M3 以太跨式被强制关门控（`dvol_stale`）。

**方案**：公开仓库 [SannyLi0322/dvol-relay](https://github.com/SannyLi0322/dvol-relay) + GitHub Actions 定时（每 6 小时）在 GitHub runner 上抓 Deribit DVOL（ETH、BTC），提交 `data/dvol_eth.csv` / `data/dvol_btc.csv`；交易机通过公开的 GitHub Contents API 读取 Base64 内容，无需 token。

## 一次性搭建（owner，约 5 分钟）

1. 在 github.com 新建仓库 `dvol-relay`（**建议 Public**：内容只有公开指数 CSV，公开仓库可让交易机无需任何 token 读取 Contents API；若选 Private，需再建一个只读 fine-grained PAT 放进交易机 `C:\trading\pool\.env` 的 `DVOL_RELAY_TOKEN`）。
2. 把本目录的 `fetch_dvol.py` 放到仓库根目录，`workflow_dvol_relay.yml` 放到 `.github/workflows/dvol_relay.yml`。
3. Actions 页手动运行一次 `dvol-relay`（workflow_dispatch），确认 `data/dvol_eth.csv` 出现。
4. 把 Contents API 地址写入 `pool_config.json` → `data.dvol_relay_base`，例如 `https://api.github.com/repos/<user>/dvol-relay/contents/data`。

也可以由 AI 代劳 1–3 步：本机安装 `gh`（`winget install GitHub.cli`）后由 owner 在浏览器完成一次 `gh auth login`，之后 `gh repo create` / 推送 / 触发 workflow 均可脚本化。无论哪种方式，**GitHub 登录这一步只能 owner 本人做**。

## 交易机侧

`fetch_dvol()` 顺序：Deribit 直连 → GitHub 中转（`data.dvol_relay_base`，若配置）→ 本地缓存。任一来源成功即刷新缓存；来源记录在 target 的 `iv_source`。
BTC 的 CSV 同时落在交易机 `C:\trading\data\dvol_btc.csv`，供后续 BTC 因子研究/上线使用。

当前线上配置（2026-11-08）：

`https://api.github.com/repos/SannyLi0322/dvol-relay/contents/data`

首次 workflow：[run 42474612717](https://github.com/SannyLi0322/dvol-relay/actions/runs/42474612717) 成功，ETH/BTC 各 1000 日；交易机验证 `iv_source=github_relay`、`iv_age_days=0`。
