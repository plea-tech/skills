一、建议的脚本清单与职责
1. prepare_extraction（抽取前准备）
项目	说明
职责	根据竞品目录和 docs_input.md 准备抽取环境，并输出「待处理文档列表」和「待抓取链接列表」，不负责具体内容抽取。
输入	竞品目录路径（如 references/Inspur）或竞品名（由脚本内解析 alias + 找目录）。
输出	① 创建 ./extracted_content/<竞品名>/，可含子目录如 text/、images/、links/；② 输出一份工作清单（如 extracted_content/<竞品名>/worklist.json 或 worklist.md），包含：每个文档的绝对/相对路径、类型（docx/pdf/pptx/xlsx）、在 docs_input 中的说明摘要；若有 links_input.md，则解析出 URL 列表，写入工作清单的「待抓取链接」部分。
大模型怎么用	Step 2 开始前调用一次；大模型根据 worklist 逐个文档用对应 skill 处理，并把结果写到 extracted_content 的约定位置。

2. fetch_links（链接内容抓取与缓存）
项目	说明
职责	读取 links_input.md（或从 prepare_extraction 的 worklist 读链接列表），抓取网页内容并落盘，避免大模型多次直接请求外网；可做简单去重与缓存。可选（--with-images）解析页面中的图片并下载到 images/，生成 links_images_manifest.md 供 Step 3 选图。
输入	竞品目录路径，或 links_input.md 路径，或 worklist 中的链接列表。
输出	在 extracted_content/<竞品名>/links/ 下保存每个链接的内容（如 /<url_hash>.html）；并生成 links_index.md：URL、标题、本地文件路径、状态。若启用 --with-images，则在 images/ 下保存网页中的图片，并生成 links_images_manifest.md（可与 merge_manifests 合并）。若某链接失败，在索引中标记「抓取失败」。
大模型怎么用	Step 2 中需要用到网页信息时，先运行此脚本，再让大模型只读本地 links/ 和 links_index.md，无需自己请求 URL。若需将网页图片纳入报告选图，请加 --with-images（建议 --min-size 120）；完成后可运行 merge_manifests 将 links 与文档 manifest 合并。

3. （可选）validate_manifest（图片清单校验/合并）
项目	说明
职责	校验「图片文件」与「图片 manifest 记录」是否一致（例如每个 images/ 下的 PNG 是否都在 manifest 中有条目）；可选：合并多个 manifest 或补全缺失字段。
输入	extracted_content/<竞品名>/（或 manifest 文件路径 + images 目录）。
输出	校验报告（缺失记录、多余文件等）或合并/补全后的单一 manifest 文件。
大模型怎么用	Step 2 完成后、Step 3 迭代 2 之前可选调用，确保写入报告时不会漏图或引用错误。

4. （可选）report_stub（报告文件名与目录）
项目	说明
职责	根据规则生成本次报告的文件名（<竞品名>_v1.0_<年月日>.docx），并确保 reports/ 存在；可选返回完整路径，供大模型写入时使用。
输入	竞品名、可选日期（默认当天）。
输出	报告完整路径或仅文件名；若需避免同一天覆盖，可在这里加序号（如 _1）。
大模型怎么用	Step 3 写 docx 前调用，保证输出路径和命名符合技能约定。

二、大模型与脚本的协作流程（对应技能三步）
Step 1（无脚本）  大模型：阅读 output_define.md、alias.md，确定竞品目录与输出大纲。Step 2 开始前  大模型：调用 prepare_extraction(竞品名或路径)          → 获得 extracted_content 目录结构 + worklist（文档列表 + 链接列表）Step 2 中  · 文档内容：    大模型：按 worklist 逐个文档，用对应 skill（docx/pdf/pptx/xlsx）抽取；           将文字整理为 markdown 写入 extracted_content/.../text/；           按技能中的图片分级规则决定是否抽取图片，保存为 PNG 到 images/，           并维护「图片 manifest」markdown（原始文档、页码、周边文字）。  · 链接内容：    大模型：调用 fetch_links(竞品目录或 worklist)            → 读取 links_index.md 与 links/* 下的本地文件，将网页信息融入理解与后续报告。  · 可选：    大模型：调用 validate_manifest(extracted_content 路径) 做图片清单校验。Step 3  大模型：读 extracted_content 下所有 markdown 与图片 manifest；          迭代 1：按 output_define.md 写出报告文字版；          可选调用 report_stub 得到报告路径；          用 docx skill 生成/写入 docx；          迭代 2：按 manifest 判断图片是否写入、生成描述、插入位置并插入图片与说明。

三、脚本边界总结
脚本不做：不对 docx/pdf/pptx/xlsx 做「理解与摘要」级别的抽取，不写最终报告正文，不决定图片是否「值得写入」报告——这些由大模型 + Claude skills 完成，符合技能里「使用 docx/pdf/pptx/xlsx 技能处理文档」的设定。
脚本做：准备目录与 worklist、抓取并缓存链接、校验/合并图片 manifest、生成报告路径与文件名，从而让大模型只关心「按 worklist 用 skill 抽取」「读本地内容写报告」。
这样划分后，你可以先实现 prepare_extraction 和 fetch_links，再视需要加 validate_manifest 和 report_stub。如果你愿意，我可以再根据你项目里 references 和 docs_input.md 的实际格式，把 prepare_extraction 的入参/出参（例如 worklist 的 JSON 结构）写得更具体，方便你直接写脚本。

---

四、使用说明（必须脚本）

请在项目根目录下执行，并先激活虚拟环境（如 `.venv/Scripts/activate`）。

**1. prepare_extraction.py**

- 作用：根据竞品目录创建 `extracted_content/<竞品名>/` 及子目录 `text/`、`images/`、`links/`，并生成 `worklist.json`。
- 参数：
  - `--ref-dir`：竞品目录的绝对或相对路径（即 `references/<竞品名>`）。
  - `--output-base`：可选，默认为当前目录；在此目录下创建 `extracted_content`。

示例（在项目根目录执行）：

```bash
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/prepare_extraction.py --ref-dir .cursor/skills/Competitor_Analysis_Report_d1/references/Inspur --output-base .
```

**2. fetch_links.py**

- 作用：抓取 `links_input.md` 或 worklist 中的 URL，将网页保存到 `extracted_content/<竞品名>/links/`，并生成 `links_index.md`。可选同时抓取网页中的图片并生成 `links_images_manifest.md`，供 Step 3 与 docx/pdf/pptx 的 manifest 一起选图。
- 参数：
  - `--output-dir`：必填，链接输出目录（即 `extracted_content/<竞品名>/links`）。
  - `--ref-dir` 或 `--worklist`：二选一。`--ref-dir` 为竞品目录（从中读 `links_input.md`）；`--worklist` 为 `worklist.json` 路径（从中读 `links` 列表）。
  - `--with-images`：可选。解析每个页面的 `<img>`，将图片下载到 `images/`，并生成 `links_images_manifest.md`（可与 merge_manifests 合并）。
  - `--images-dir`：与 `--with-images` 同用；默认 `output-dir` 的上级目录下的 `images`。
  - `--min-size N`：与 `--with-images` 同用；宽或高小于 N 像素的图片不保存（默认 0；建议 120 过滤 logo/图标）。需安装 Pillow 才生效。
  - `--manifest`：与 `--with-images` 同用；manifest 输出路径，默认 `extracted_content/<竞品名>/links_images_manifest.md`。

示例：

```bash
# 方式一：从竞品目录读 links_input.md
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/fetch_links.py --ref-dir .cursor/skills/Competitor_Analysis_Report_d1/references/Inspur --output-dir extracted_content/Inspur/links

# 方式二：从 worklist.json 读链接列表
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/fetch_links.py --worklist extracted_content/Inspur/worklist.json --output-dir extracted_content/Inspur/links

# 同时抓取网页中的图片到 images/ 并生成 links_images_manifest.md（建议加 --min-size 120 过滤小图）
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/fetch_links.py --worklist extracted_content/Inspur/worklist.json --output-dir extracted_content/Inspur/links --with-images --min-size 120
```
# 推荐的测试方式
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/fetch_links.py --ref-dir .cursor/skills/Competitor_Analysis_Report_d1/references/Test --output-dir extracted_content/Test/links --with-images --min-size 120

**3. run_extraction.py**（Step 2 批量抽取：按 worklist 执行 run_markitdown + extract_*_images）

- 作用：读 worklist.json，对其中每个 docx/pptx/pdf 执行 run_markitdown（输出到 text/）和对应的 extract_*_images（输出到 images/），无需逐条手动调用。
- 参数：`--worklist <worklist.json 路径>` 或 `--extracted-dir <extracted_content/竞品名>`（二选一）；`--min-size N` 抽图过滤小图（默认 120）。
- 示例：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/run_extraction.py --extracted-dir extracted_content/Inspur` 或 `--worklist extracted_content/Inspur/worklist.json`

**4. run_markitdown.py**（docx/pptx/pdf 转 markdown，不依赖 pandoc；Python 3.13+ 下避免 aifc 报错）

- 用法与 `python -m markitdown` 相同，例如：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/run_markitdown.py <文档路径> -o <输出.md>`。

**5. extract_docx_images.py**（从 DOCX 抽取内嵌图片；可过滤小图；manifest 含序号与所在段落文字）

- 参数：`<docx路径>`、`<输出目录>`；`--min-size N` 不抽取宽或高小于 N 像素的图片（默认 120，设为 0 则不过滤）；可选 `--manifest <路径>`。
- 生成的 manifest 表格包含：序号、文件名、**周边文字（所在段落）**、说明。与 PDF/PPTX 抽图脚本一致，便于迭代2 选图。
- 示例：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/extract_docx_images.py "path/to/file.docx" extracted_content/Inspur/images --min-size 120 --manifest extracted_content/Inspur/docx_images_manifest.md`

**6. extract_pptx_images.py**（从 PPTX 抽取内嵌图片；可过滤小图；manifest 含幻灯片号与该页原文摘要）

- 参数：`<pptx路径>`、`<输出目录>`；`--min-size N` 不抽取宽或高小于 N 像素的图片（默认 120）；可选 `--manifest <路径>`。
- 生成的 manifest 表格包含：幻灯片号、文件名、**周边文字（该页原文摘要）**、说明。
- 示例：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/extract_pptx_images.py "path/to/file.pptx" extracted_content/Inspur/images --min-size 120 --manifest extracted_content/Inspur/pptx_images_manifest.md`

**7. extract_pdf_images.py**（从 PDF 抽取内嵌图片，不依赖 pdfimages/poppler；可过滤 LOGO/图标；manifest 含该页原文摘要供选图用）

- 参数：`<pdf路径>`、`<输出目录>`；`--min-size N` 不抽取宽或高小于 N 像素的图片（默认 120，设为 0 则不过滤）；可选 `--manifest <路径>`。
- 生成的 manifest 表格包含：页码、文件名、**周边文字（该页原文摘要）**、说明。选图时先读该列，可区分 logo 与架构图等，再结合大模型看图决定是否插入及位置。
- 示例：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/extract_pdf_images.py "path/to/file.pdf" extracted_content/Inspur/images --min-size 120 --manifest extracted_content/Inspur/pdf_images_manifest.md`

**Step 3 迭代2（必须执行）**  
生成报告文字版 docx 后，必须执行迭代2：① 先阅读各 manifest（extract_docx_images、extract_pptx_images、extract_pdf_images 生成的 manifest 均含「页码/序号/幻灯片号、文件名、周边文字」）；② 结合周边文字初选候选图后，**必须用大模型看图**判断是否值得插入及插入章节、图注（与章节直接相关、能支撑结论、非 LOGO/图标）；③ 再根据判断结果编写放置清单，运行 **insert_report_images.py** 插入 docx。不得仅凭页码或文件名选图，否则易出现图与文字不一致（如误插 logo）。未执行迭代2 则报告视为未完成。

**8. insert_report_images.py**（Step 3 迭代2：按放置清单将图片插入报告 docx）

- 作用：读取「图片放置清单」JSON，在目标 docx 中定位到指定标题（章节），在该标题后插入图片并添加图注。
- 参数：`--docx` 目标报告 docx 路径；`--placement` 放置清单 JSON 文件路径（格式见下）。
- 放置清单 JSON 格式：`[{"heading": "2.1 架构&技术分析", "image": "extracted_content/Inspur/images/xxx/page_1_img_0.png", "caption": "系统架构图"}, ...]`。`heading` 为 docx 中出现的标题文字（可写一级或二级标题），脚本在该标题所在段落后插入 `image` 并添加 `caption` 段落。
- 示例：`python .cursor/skills/Competitor_Analysis_Report_d1/scripts/insert_report_images.py --docx reports/Inspur_v1.0_20260211.docx --placement extracted_content/Inspur/image_placement.json`

---

五、使用说明（可选脚本）

**3. validate_manifest.py**

- 作用：校验 `images/` 下图片文件与「图片 manifest」markdown 是否一致（有文件无记录、有记录无文件），可选将报告写入文件。
- 参数：
  - `--extracted-dir`：`extracted_content/<竞品名>` 的路径；脚本会在其下查找 `images_manifest.md` 与 `images/`。
  - 或 `--manifest` + `--images-dir`：分别指定 manifest 文件与图片目录。
  - `--report`：将校验报告写入该文件；不指定则打印到 stdout。
  - `--merge`：与 `--extracted-dir` 配合时，将找到的 manifest 合并写入到抽取根目录下的 `images_manifest.md`。

示例：

```bash
# 使用抽取目录（自动查找 images_manifest.md 与 images/）
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/validate_manifest.py --extracted-dir extracted_content/Inspur

# 将报告写入文件
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/validate_manifest.py --extracted-dir extracted_content/Inspur --report extracted_content/Inspur/manifest_validation.md
```

**4. report_stub.py**

- 作用：生成报告文件名（`<竞品名>_v1.0_<年月日>.docx`），并确保 `reports/` 目录存在；可选避免同一天覆盖。
- 参数：
  - `--competitor`：竞品名（必填）。
  - `--date`：可选，格式 YYYYMMDD，默认当天。
  - `--reports-root`：可选，默认为当前目录；在其下创建或使用 `reports/`。
  - `--avoid-overwrite`：若当日文件已存在，在文件名后加 _1、_2 等序号。
  - `--print-path-only`：只打印最终报告路径，便于脚本串联。

示例：

```bash
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/report_stub.py --competitor Inspur --reports-root .

# 只输出路径，便于大模型写入
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/report_stub.py --competitor Inspur --print-path-only
```

**5. resolve_competitor.py**

- 作用：根据竞品名或别名（如「浪潮」「LC」）解析出 `references` 下的竞品目录路径，便于得到 `prepare_extraction` 的 `--ref-dir`。
- 参数：
  - `--competitor`：竞品名或别名（必填，不区分大小写）。
  - `--refs-root`：可选，`references` 目录路径；不指定则从脚本所在技能目录推导。
  - `--print-dir-only`：只打印竞品目录绝对路径。

示例：

```bash
# 从项目根执行，使用默认 references（技能目录下）
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/resolve_competitor.py --competitor 浪潮

# 只输出目录路径，与 prepare_extraction 串联
python .cursor/skills/Competitor_Analysis_Report_d1/scripts/resolve_competitor.py --competitor Inspur --print-dir-only
```