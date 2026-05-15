# Semantic Scholar API Reference (Paper Data + Author Data)

更新日期：2026-05-09  
调研范围：`Paper Data`、`Author Data`  
官方来源：

1. `https://api.semanticscholar.org/api-docs/#tag/Paper-Data`
2. `https://api.semanticscholar.org/api-docs/#tag/Author-Data`
3. `https://api.semanticscholar.org/graph/v1/swagger.json`

---

## 0) 基础调用信息

基础 URL：`https://api.semanticscholar.org/graph/v1`

推荐请求头：

1. `Accept: application/json`
2. `x-api-key: <YOUR_API_KEY>`（可选但建议；配额和稳定性更好）
3. 统一脚本路径写法：`scripts/scholar-search.py`。

通用参数约定：

1. `fields` 为逗号分隔字符串，支持点号子字段（如 `authors.name`、`citations.title`）。
2. `offset` 为偏移分页参数（从 `0` 开始）。
3. `openAccessPdf` 是布尔筛选开关，按官方描述“不接受值”，通常写成仅带参数名：`...&openAccessPdf&...`。

---

## A) Paper Data

### A1. Paper relevance search

- Method: `GET`
- Path: `/paper/search`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `query` | query | 是 | string | - | 纯文本查询；不支持特殊查询语法；官方示例提示连字符词建议改为空格。 |
| `fields` | query | 否 | string | `paperId,title` | 指定返回字段，逗号分隔；支持点号子字段。 |
| `publicationTypes` | query | 否 | string | - | 论文类型过滤（如 `Review,JournalArticle`）。 |
| `openAccessPdf` | query | 否 | string(flag) | - | 仅返回有公开 PDF 的论文；不传值。 |
| `minCitationCount` | query | 否 | string | - | 最低引用次数过滤，如 `200`。 |
| `publicationDateOrYear` | query | 否 | string | - | 发表日期/年份区间过滤（格式见文末统一说明）。 |
| `year` | query | 否 | string | - | 年份或年份区间过滤（格式见文末统一说明）。 |
| `venue` | query | 否 | string | - | 期刊/会议过滤，支持逗号分隔，也支持 ISO4 缩写。 |
| `fieldsOfStudy` | query | 否 | string | - | 学科过滤，逗号分隔。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 100`。 |

补充限制：

1. 官方说明该端点最多返回 1000 条 relevance 排序结果。
2. 实测常见额外限制：`offset + limit < 1000`（超限常见 400）。

示例：

```bash
python scripts/scholar-search.py --endpoint paper/search --params '{"query":"large language model","limit":10,"offset":0,"fields":"paperId,title,year,authors,abstract,citationCount"}'
```

### A1b. Paper bulk search

- Method: `GET`
- Path: `/paper/search/bulk`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `query` | query | 是 | string | - | 纯文本查询。 |
| `token` | query | 否 | string | - | 分页游标；使用上一页响应中的 token 获取下一页。 |
| `fields` | query | 否 | string | `paperId,title` | 指定返回字段，逗号分隔；支持点号子字段。 |
| `sort` | query | 否 | string | - | 排序字段，按官方支持值使用。 |
| `publicationTypes` | query | 否 | string | - | 论文类型过滤。 |
| `openAccessPdf` | query | 否 | string(flag) | - | 仅返回有公开 PDF 的论文；不传值。 |
| `minCitationCount` | query | 否 | string | - | 最低引用次数过滤。 |
| `publicationDateOrYear` | query | 否 | string | - | 发表日期/年份区间过滤。 |
| `year` | query | 否 | string | - | 年份或年份区间过滤。 |
| `venue` | query | 否 | string | - | 期刊/会议过滤。 |
| `fieldsOfStudy` | query | 否 | string | - | 学科过滤。 |

补充说明：

1. 该端点适合遍历较大的查询结果集，分页使用 `token` 而不是 `offset`。
2. 当前脚本会按 endpoint 自动选择 GET/POST；本端点使用 GET，POST batch 端点见 A8 与 B4。

示例：

```bash
python scripts/scholar-search.py --endpoint paper/search/bulk --params '{"query":"large language model","year":"2024-2026","fields":"paperId,title,year,authors,citationCount,url"}'
```

### A2. Paper title search (single best match)

- Method: `GET`
- Path: `/paper/search/match`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `query` | query | 是 | string | - | 纯文本标题查询，返回最接近的一条。 |
| `fields` | query | 否 | string | `paperId,title` | 指定返回字段。 |
| `publicationTypes` | query | 否 | string | - | 论文类型过滤。 |
| `openAccessPdf` | query | 否 | string(flag) | - | 仅返回有公开 PDF 的论文。 |
| `minCitationCount` | query | 否 | string | - | 最低引用次数过滤。 |
| `publicationDateOrYear` | query | 否 | string | - | 日期/年份区间过滤。 |
| `year` | query | 否 | string | - | 年份区间过滤。 |
| `venue` | query | 否 | string | - | 期刊/会议过滤。 |
| `fieldsOfStudy` | query | 否 | string | - | 学科过滤。 |

补充限制：

1. 只返回单条最高匹配结果；无匹配通常返回 404。

示例：

```bash
python scripts/scholar-search.py --endpoint paper/search/match --params '{"query":"Attention Is All You Need","fields":"paperId,title,year,authors"}'
```

### A3. Paper details

- Method: `GET`
- Path: `/paper/{paper_id}`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `paper_id` | path | 是 | string | - | 论文标识（支持多种 ID，见下方“paper_id 支持格式”）。 |
| `fields` | query | 否 | string | `paperId,title` | 指定返回字段。 |

`paper_id` 支持格式（官方列举）：

1. `<sha>`（Semantic Scholar paperId）
2. `CorpusId:<id>`
3. `DOI:<doi>`
4. `MAG:<id>`
5. `ACL:<id>`
6. `PMID:<id>`
7. `PMCID:<id>`
8. `URL:<url>`（限定识别站点）

示例：

```bash
python scripts/scholar-search.py --endpoint paper/DOI:10.1038/nrn3241 --params '{"fields":"paperId,title,year,authors,abstract,referenceCount,citationCount,externalIds"}'
```

### A4. Paper authors

- Method: `GET`
- Path: `/paper/{paper_id}/authors`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `paper_id` | path | 是 | string | - | 论文 ID（支持格式同 A3）。 |
| `fields` | query | 否 | string | `authorId,name` | 作者返回字段。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 1000`。 |

示例：

```bash
python scripts/scholar-search.py --endpoint paper/CorpusId:215416146/authors --params '{"fields":"authorId,name,hIndex,paperCount","limit":20}'
```

### A5. Paper citations

- Method: `GET`
- Path: `/paper/{paper_id}/citations`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `paper_id` | path | 是 | string | - | 论文 ID（支持格式同 A3）。 |
| `publicationDateOrYear` | query | 否 | string | - | 对 citing paper 的日期/年份区间过滤。 |
| `fields` | query | 否 | string | `paperId,title` | 返回字段；常见字段在 `citingPaper` 下。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 1000`。 |

示例：

```bash
python scripts/scholar-search.py --endpoint paper/CorpusId:215416146/citations --params '{"fields":"contexts,isInfluential,citingPaper.title,citingPaper.year","limit":20}'
```

### A6. Paper references

- Method: `GET`
- Path: `/paper/{paper_id}/references`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `paper_id` | path | 是 | string | - | 论文 ID（支持格式同 A3）。 |
| `fields` | query | 否 | string | `paperId,title` | 返回字段；常见字段在 `citedPaper` 下。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 1000`。 |

示例：

```bash
python scripts/scholar-search.py --endpoint paper/CorpusId:215416146/references --params '{"fields":"contexts,isInfluential,citedPaper.title,citedPaper.year","limit":20}'
```

### A7. Paper autocomplete

- Method: `GET`
- Path: `/paper/autocomplete`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `query` | query | 是 | string | - | 论文补全查询串；官方说明会截断到前 100 个字符。 |

补充说明：

1. 官方未定义 `limit` 参数；请不要依赖 `limit` 控制数量。

示例：

```bash
python scripts/scholar-search.py --endpoint paper/autocomplete --params '{"query":"semanti"}'
```

### A8. Paper batch details

- Method: `POST`
- Path: `/paper/batch`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `fields` | query | 否 | string | `paperId,title` | 指定返回字段；放在 `--params` 中，不放进 body。 |
| `ids` | body | 是 | string[] | - | 论文 ID 数组；放在 `--payload` 中，形如 `{"ids":[...]}`。 |

限制：

1. 一次最多 500 个 paper ID。
2. 一次最多返回 10 MB 数据。
3. 一次最多返回 9999 条 citations。

示例：

```bash
python scripts/scholar-search.py --endpoint paper/batch --params '{"fields":"paperId,title,year,citationCount"}' --payload '{"ids":["649def34f8be52c8b66281af98ae884c09aef38b","ARXIV:2106.15928"]}'
```

### A9. Snippet text search

- Method: `GET`
- Path: `/snippet/search`
- 官方文档：`Snippet-Text / get_snippet_search`

功能说明：

1. 用于按短语或关键词在论文片段（snippet）层面检索文本命中结果。
2. 典型用途是“先用 `paper/search` 找候选论文，再用 snippet 搜索验证特定术语在上下文中的出现位置”。
3. 适合做术语定位、证据摘录、上下文核查，不替代论文级检索。

校验（2026-05-09，官方 swagger 与脚本实测）：

1. `query` 必填；缺失或空字符串会返回 `400`（`Missing required parameter: 'query'`）。
2. 官方 swagger 当前列出 `fields`、`paperIds`、`authors`、`minCitationCount`、`insertedBefore`、`publicationDateOrYear`、`year`、`venue`、`fieldsOfStudy`、`query`、`limit`。
3. `limit` 默认 `10`，上限 `1000`；`limit=1001` 会返回 `400`。
4. 官方 swagger 未列出 `offset`，不应依赖分页行为。
5. 实测 `fields=snippet,paper.title` 与 `fields=score,paper,snippet` 均返回 `400`，因此当前技能默认不为 `snippet/search` 传 `fields`。

常用参数：

| 参数 | 位置 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- | --- |
| `query` | query | 是 | string | 片段检索查询文本（建议具体、可判别）。 |
| `fields` | query | 否 | string | 官方 swagger 列出该参数，但实测常见字段组合会被拒绝；默认不要传。 |
| `paperIds` | query | 否 | string | 限定论文 ID 集合。 |
| `authors` | query | 否 | string | 作者过滤。 |
| `minCitationCount` | query | 否 | string | 最低引用次数过滤。 |
| `insertedBefore` | query | 否 | string | 限定 snippet 插入时间。 |
| `publicationDateOrYear` | query | 否 | string | 发表日期/年份区间过滤。 |
| `year` | query | 否 | string | 年份过滤。 |
| `venue` | query | 否 | string | 期刊/会议过滤。 |
| `fieldsOfStudy` | query | 否 | string | 学科过滤。 |
| `limit` | query | 否 | integer | 返回条数控制；默认 `10`，最大 `1000`。 |

使用建议：

1. 优先在主题已经收敛后使用（如已定位到具体子问题）。
2. 与 `paper/search` 配合使用，避免只依赖 snippet 结果做结论。
3. 查询词建议先用英文术语原词，再按同义词做 1 轮扩展。
4. 最小且已实测可用的请求是 `query`（可选 `limit`）；不要默认加 `fields`。

示例：

```bash
python scripts/scholar-search.py --endpoint snippet/search --params '{"query":"transformer architecture","limit":5}'
```

---

## B) Author Data

### B1. Author search

- Method: `GET`
- Path: `/author/search`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `query` | query | 是 | string | - | 作者名纯文本查询；官方说明连字符词可能无匹配（建议改空格）。 |
| `fields` | query | 否 | string | `authorId,name` | 返回字段。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 1000`。 |

补充限制：

1. 实测 `offset + limit >= 10000` 会报错，建议控制在 10000 以内窗口。

示例：

```bash
python scripts/scholar-search.py --endpoint author/search --params '{"query":"Yann LeCun","fields":"name,url,paperCount,citationCount","limit":5,"offset":0}'
```

### B2. Author details

- Method: `GET`
- Path: `/author/{author_id}`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `author_id` | path | 是 | string | - | 作者 ID（如 `1741101`）。 |
| `fields` | query | 否 | string | `authorId,name` | 指定返回字段。 |

示例：

```bash
python scripts/scholar-search.py --endpoint author/1741101 --params '{"fields":"name,affiliations,paperCount,citationCount,hIndex"}'
```

### B3. Author papers

- Method: `GET`
- Path: `/author/{author_id}/papers`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `author_id` | path | 是 | string | - | 作者 ID。 |
| `publicationDateOrYear` | query | 否 | string | - | 论文日期/年份区间过滤。 |
| `offset` | query | 否 | integer | `0` | 偏移分页起点。 |
| `limit` | query | 否 | integer | `100` | 返回条数，官方约束 `<= 1000`。 |
| `fields` | query | 否 | string | `paperId,title` | 返回字段；可请求论文子字段。 |

补充说明：

1. 官方 swagger 未定义 `sort` 参数，不建议依赖未文档化排序行为。

示例：

```bash
python scripts/scholar-search.py --endpoint author/1741101/papers --params '{"publicationDateOrYear":"2019:2024","fields":"paperId,title,year,citationCount","limit":20}'
```

### B4. Author batch details

- Method: `POST`
- Path: `/author/batch`

| 参数 | 位置 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `fields` | query | 否 | string | `authorId,name` | 指定返回字段；放在 `--params` 中，不放进 body。 |
| `ids` | body | 是 | string[] | - | 作者 ID 数组；放在 `--payload` 中，形如 `{"ids":[...]}`。 |

限制：

1. 一次最多 1000 个 author ID。
2. 一次最多返回 10 MB 数据。

示例：

```bash
python scripts/scholar-search.py --endpoint author/batch --params '{"fields":"authorId,name,hIndex,citationCount"}' --payload '{"ids":["1741101","1780531"]}'
```

---

## C) 日期参数格式（统一说明）

### C1. `publicationDateOrYear`

接受 `<startDate>:<endDate>`，每项可写为 `YYYY-MM-DD`、`YYYY-MM`、`YYYY`，端点支持开区间。

示例：

1. `2019-03-05`
2. `2019-03`
3. `2019`
4. `2016-03-05:2020-06-06`
5. `1981-08-25:`
6. `:2015-01`
7. `2015:2020`

### C2. `year`

支持单年、闭区间与开区间。

示例：

1. `2019`
2. `2016-2020`
3. `2010-`
4. `-2015`

---

## D) 已校正项（针对“参数介绍缺失与不一致”）

1. 已补全 Paper Data 与 Author Data 全部主要端点的参数说明（位置/必填/类型/默认值/含义）。
2. 已明确 `/paper/autocomplete` 不应将 `limit` 作为官方参数依赖。
3. 已补充 GET `/paper/search/bulk`。
4. 已补充 POST `/paper/batch` 与 `/author/batch`，脚本使用 `--payload` 传 body。
5. 已根据官方 swagger 更新 `/snippet/search` 参数说明。

