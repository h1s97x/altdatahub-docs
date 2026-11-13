# altdatahub（TypeScript）

封装中国人民银行征信中心「**金融信用信息基础数据库替代数据通**」产品的第三方 TypeScript SDK
（**非官方**，与征信中心无隶属关系）。

- **零运行时依赖**：`fetch`（Node 18+ 内置）+ `node:test`，开发依赖只有 `typescript`、`@types/node`；
- **类型是生成的**：`src/types.ts`（2700 行、51 个产品接口 + 12 个子结构）由 `tools/gen_code.py`
  从 `catalog/products.json` 产出，`gen_code.py --check` 在 CI 里守着；
- **全程 `Promise`**：与 Python 版的唯一签名差异，因为 `fetch` 是异步的。

## 安装与构建

```bash
cd sdks/typescript
npm ci
npm run build      # tsc → dist/
npm test           # build + node --test dist/tests/*.test.js
```

## 用法

```ts
import { HubClient, PRODUCT_CODES, type S0101BasicProfile } from 'altdatahub';

// 离线（把上游响应喂进模型层，不发网络请求）
const offline = new HubClient(
  new MappingTransport({ S0101: { data: [{ entType: '有限责任公司' }] } }),
);
const rows = await offline.enterpriseBasic<S0101BasicProfile>(PRODUCT_CODES.S0101, {
  entName: '贵州茅台',
});
rows[0]?.entType; // '有限责任公司'
rows[0]?.raw;     // 原始对象，分册未覆盖的新字段不会丢

// 真实调用：从 EDS_* 环境变量取网关参数
const client = HubClient.fromEnv();
await client.enterpriseBasic(PRODUCT_CODES.S0101, {
  entName: '贵州茅台',
  page: '1',
  pageSize: '20',
});
```

## 公共参数（环境变量）

缺任何一个都会在**本地**报错并列出变量名，不回显取值。

| 环境变量 | 说明 |
|---|---|
| `EDS_BASE_URL` | 网关地址 |
| `EDS_ACCOUNT` | 授权字串（凭据） |
| `EDS_OPERATE_USER_ID` / `EDS_OPERATE_USER_NAME` | 用户编号 / 查询用户名 |
| `EDS_SCENE` | 来源系统简称（大写英文字母） |
| `EDS_ORG_ID` / `EDS_ORG_ID_NAME` | 查询机构编号 / 机构名 |
| `EDS_VALID_DAY` | 选填，数据有效期（0=每次查最新），默认 0 |
| `EDS_TIMEOUT` | 选填，**秒**（内部换算成毫秒），默认 30 |
| `EDS_SERVICE_CODE_PATTERN` | 选填，服务号模板，默认 `izxzx{product_code}` |

## 与 Python 版的对应关系

| Python | TypeScript |
|---|---|
| `client.enterprise_basic(code, entName="x")` | `client.enterpriseBasic(code, { entName: 'x' })` |
| `client.from_env()` | `HubClient.fromEnv()` |
| `EdsConfig(...)` 的 `org_id` | `EdsConfig` 的 `orgId`（camelCase） |
| `list[Record]` | `Promise<AnyRecord[]>`，可标注泛型 |
| `EdsBizError.retryable` | 同名同义 |

错误分类、重试语义、错误码判定、「先判错再取数据行」的链路顺序与 Python 版逐条一致 ——
那边的 4 个业务码（1000/2000/3000/9999）与可重试性在这里用同一张表。

## 未确认项

响应信封（`data[].data`）与错误码字段名（`code` / `msg`）已确认；仍待确认服务号清单、
`eds_validday` 类型原文 —— 与 Python 版共享同一批未知，
详见 [`docs/api/transport.md`](../../docs/api/transport.md)。
