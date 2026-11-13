# Python SDK

## 离线先跑通模型层

传输实现可注入。用 `MappingTransport` 把上游响应喂进模型层，无需任何凭据：

```python
from altdatahub import HubClient, MappingTransport, PRODUCT_CODES

client = HubClient(MappingTransport({"S0101": {"data": [{"entType": "有限责任公司"}]}}))
row = client.enterprise_basic(PRODUCT_CODES.S0101, entName="贵州茅台")[0]
row.entType      # '有限责任公司'
row.raw          # 分册未覆盖的新字段仍保留在这里
```

不传 transport 时默认是 `PendingTransport`：查询会显式抛 `SpecPendingError`，
不会静默返回空列表，也不会发半成品请求；`categories()` 等本地能力照常可用。

## 在线查询

```python
from altdatahub import HubClient, PRODUCT_CODES

client = HubClient.from_env()   # 从 EDS_* 环境变量构造 HttpTransport
rows = client.enterprise_basic(
    PRODUCT_CODES.S0101, entName="贵州茅台",
    page="1", pageSize="20", queryReason="贷前审查",
)
```

`HubClient.from_env()` 缺变量时只报**变量名**，不回显取值；`EdsConfig.__repr__` 也对
`eds_account` 打码。业务参数不许以 `eds_` 开头（会顶掉凭据字段，组装时直接拒绝）。

## 错误与降级

业务错误码按值判定：`1000` / `2000` 参数问题不重试，`3000` 无权限不重试，
`9999` 系统错误有界退避。`data: []` 是正常成功，码表里没有「查无数据」。

!!! warning "网关未联调"
    响应信封的数据行位置按候选路径试探；在线查询失败不等于查无记录，
    更不能用模拟数据代替。详见[传输契约](../contract/index.md)。
