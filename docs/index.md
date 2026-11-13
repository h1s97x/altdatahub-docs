---
hide:
  - toc
search:
  boost: 2
---

<div class="landing">

  <section class="landing-hero">
    <div class="landing-hero__inner">
      <p class="landing-eyebrow">第三方 SDK · 非官方实现</p>
      <h1>把 51 个数据产品<br>收敛成<span>一套可验证的契约</span></h1>
      <p class="landing-lead">
        金融信用信息基础数据库替代数据通的第三方 Python SDK、7 语言类型库、
        能力服务与 AI 接入层。离线产品目录完全可用，在线查询保持诚实降级。
      </p>
      <div class="landing-badges">
        <span class="landing-badge">v0.1.0</span>
        <span class="landing-badge">纯离线目录可用</span>
        <span class="landing-badge">7 语言 SDK</span>
        <span class="landing-badge">核心零第三方依赖</span>
      </div>
      <div class="landing-actions">
        <a class="md-button md-button--primary" href="getting-started/install/">快速开始 →</a>
        <a class="md-button" href="api/">API 文档</a>
        <a class="md-button" href="mcp/">MCP 文档</a>
        <a class="md-button" href="guides/toolchain/">开发工具</a>
      </div>
    </div>
  </section>

  <section class="landing-metrics">
    <div class="landing-metric"><strong>10</strong><span>产品大类</span></div>
    <div class="landing-metric"><strong>51</strong><span>productCode</span></div>
    <div class="landing-metric"><strong>557</strong><span>顶层字段</span></div>
    <div class="landing-metric"><strong>12</strong><span>子结构</span></div>
    <div class="landing-metric"><strong>7</strong><span>语言 SDK</span></div>
    <div class="landing-metric"><strong>5</strong><span>能力端点</span></div>
  </section>

  <section class="landing-section">
    <p class="landing-kicker">DOCUMENTATION</p>
    <h2 class="landing-section-title">三大板块，各取所需</h2>
    <div class="landing-grid">
      <a class="landing-card" href="api/">
        <span class="landing-card__index">01</span>
        <h3>API 文档</h3>
        <p>总览与鉴权、逐端点参数表与 curl 示例、统一响应、错误处置、数据契约与能力矩阵。</p>
        <span class="landing-card__more">查看端点参考 →</span>
      </a>
      <a class="landing-card" href="mcp/">
        <span class="landing-card__index">02</span>
        <h3>MCP 文档</h3>
        <p>5 个 tool 的 inputSchema 与 JSON-RPC 示例、stdio / Streamable HTTP 双 transport、部署配置。</p>
        <span class="landing-card__more">查看 Tools 参考 →</span>
      </a>
      <a class="landing-card" href="guides/toolchain/">
        <span class="landing-card__index">03</span>
        <h3>开发工具</h3>
        <p>安装与 CLI、Python / 多语言 SDK、能力服务部署、生成器与门禁、联调镜像、排障 FAQ。</p>
        <span class="landing-card__more">查看工具链 →</span>
      </a>
    </div>
  </section>

  <section class="landing-section">
    <p class="landing-kicker">DESIGN</p>
    <h2 class="landing-section-title">为什么是这套设计</h2>
    <div class="landing-features">
      <div class="landing-feature">
        <h3>强类型模型</h3>
        <p>51 个产品 + 12 个子结构 dataclass；未知字段落 <code>raw</code>，前向兼容不丢数据。</p>
      </div>
      <div class="landing-feature">
        <h3>单一真源</h3>
        <p><code>schema.json</code> / <code>capabilities.json</code> / <code>vectors.json</code> 驱动全部派生，手改必红。</p>
      </div>
      <div class="landing-feature">
        <h3>跨语言一致</h3>
        <p>24 个契约向量由 7 种语言全量参数化消费，行为漂移在 CI 里立刻暴露。</p>
      </div>
      <div class="landing-feature">
        <h3>凭据不下发</h3>
        <p>8 个 <code>eds_*</code> 公共参数只在能力服务端，调用方与 AI 客户端都不接触。</p>
      </div>
      <div class="landing-feature">
        <h3>脱敏后公开</h3>
        <p>白名单 → 脱敏 → sha256 manifest；本站所有原始文档都来自这份快照。</p>
      </div>
      <div class="landing-feature">
        <h3>诚实降级</h3>
        <p>缺凭据返回 <code>success=false</code> + <code>degrade_reason</code>，不伪造任何企业数据。</p>
      </div>
    </div>
  </section>

  <section class="landing-quick">
    <h2>三步跑通离线能力</h2>
    <pre><code>pip install --index-url https://pypi.cnb.cool/h1s97x/pypi/-/packages/simple altdatahub
altdatahub categories
altdatahub schema S0101</code></pre>
    <p>离线目录不需要任何凭据。安装方式、7 语言构建命令与统一门禁见
      <a href="getting-started/install/">安装与 CLI</a> 与 <a href="guides/toolchain/">工具链</a>。</p>
  </section>

  <aside class="landing-note">
    <strong>诚实口径（先读）</strong>
    <p>
      本项目是<b>第三方实现</b>，非征信中心官方发布，与征信中心无隶属关系。
      离线目录能力完全可用；<b>在线查询尚未与真实 EDS 网关联调</b>，缺 <code>EDS_*</code> 凭据时返回
      <code>success=false</code> + <code>degrade_reason</code>，这是「数据源未接入」，不是「查无记录」。
      <code>data: []</code> 才是正常成功。本站<b>不提供</b>在线调试台、试用 Token 或公开可调用接口。
      详见 <a href="guides/troubleshooting/">排障 FAQ</a> 与 <a href="api/">API 总览</a>。
    </p>
  </aside>

  <footer class="landing-footer">
    <span>给 AI 读：</span>
    <a href="llms.txt">llms.txt</a>
    <a href="llms-full.txt">llms-full.txt</a>
    <span>更多：</span>
    <a href="contract/capabilities/">能力矩阵</a>
    <a href="reference/">原始文档镜像</a>
    <a href="changelog/">变更记录</a>
  </footer>

</div>
