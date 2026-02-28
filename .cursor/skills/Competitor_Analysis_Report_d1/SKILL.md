---
name: Competitor_Analysis_Report_d1
description: 编写竞品分析报告v1.0版本(初始版本)
---

你的角色是一个产品经理，任务是编写竞品分析报告. 你需要阅读相关的inputs, 按 output_define.md 要求的大纲进行输出，并**严格遵循 output_define.md 中的「文档风格定义」**（版式、字体、标题与段落、图注等），使生成的 docx 统一、易读、便于打印与归档.

# 【必须】执行脚本前的环境要求
- **所有本技能涉及的 Python 脚本，必须在项目 Python 虚拟环境中执行。**
- 执行任何脚本之前，必须先激活项目虚拟环境：在项目根目录下执行 `.venv\Scripts\Activate.ps1`（Windows PowerShell）或 `source .venv/bin/activate`（Linux/macOS），再运行 `python .../scripts/xxx.py`。未激活虚拟环境会导致 run_markitdown 等依赖失败（如 onnxruntime 与系统 Python 版本冲突）。
- 若通过 run_extraction.py 等脚本间接调用 run_markitdown，同样需在已激活虚拟环境的 shell 中执行。
- 后续提到的<项目目录>, 如果没有, 则为技能当前目录.

# 输入
-在references目录下，每个竞争对手都有一个对应的子目录. 例如Oracle对应的目录为: references/oracle.
-用户会指定竞争对手的名字，你根据这个名字(忽略大小写)找到对应的子目录. 如果找不到，用户可能使用了竞争对手的别名，请阅读alias.md文件查找别名.
-寻找输入目录时, 不要受.gitignore文件的影响.
-输入分两种形式: 本地文件和网页链接
-对于本地文件:子目录下有一个docs_input.md，用来说明每个文档名字和内容. 文档的语言包括中文和英文.
-对于网页链接:子目录下有一个可选的links_input.md，用来说明竞品分析用到的一些网页链接，你需要读取这些链接的信息.
-在scripts目录下, 有一些技能实现脚本.

# 输出
-输出格式为docx
-输出位置为 <项目目录>/reports/ . 文件名为: <竞争对手名>_v1.0_<年月日>.docx
-输出内容参考 output_define.md 中的**大纲与章节定义**及**内容与撰写要求**；输出版式与样式参考 output_define.md 的**文档风格定义**。生成 docx 时应先应用或配置样式再写入内容（参见 output_define.md §9 实施说明）。
-**内容充实**：有抽取材料的章节应**充分展开**，写出要点、数据、案例或对比，可用列表/表格；避免每节仅一两句概括导致内容干涩。仅当某节在输入中确实无对应材料时才用 TODO；有材料处务必写实、写透，不自行发挥但也不过度压缩。

# 处理过程
step 1. 阅读 output_define.md，理解输出的目标内容（含**大纲**、**内容与撰写要求**、**各章节撰写要点**、**文档风格定义**）。内容与撰写要点用于 Step 3 写草稿时避免章节过短、过干。
step 2. 检查<项目目录>/extracted_content目录下是否已经有抽取的内容. 如果没有,则运行抽取脚本, 抽取原始文件的内容，包括文字和图片. 抽取的内容统一放在 <项目目录>/extracted_content 目录下. 文档处理约定如下（方案1，不依赖系统安装 pandoc）：
-docx、pptx 的文字抽取：使用本技能 scripts 下的 run_markitdown.py，将文档转为 markdown。命令示例：python <技能目录>/scripts/run_markitdown.py <文档路径> -o <输出.md>。图片抽取：使用 extract_docx_images.py / extract_pptx_images.py，与 PDF 一致地输出到 images/ 并生成 manifest（序号或幻灯片号、文件名、周边文字）。命令示例：python .../extract_docx_images.py <docx路径> <输出目录> --min-size 120 [--manifest <manifest.md>]；python .../extract_pptx_images.py <pptx路径> <输出目录> --min-size 120 [--manifest <manifest.md>]。
-pdf：文字抽取用 run_markitdown.py（同上，markitdown 内建 pdfminer）；图片抽取用 extract_pdf_images.py，不依赖系统 pdfimages/poppler。为减少 LOGO、图标等小图，请加上 --min-size 120（默认 120，即宽或高小于 120 像素的不抽取；可按需调大如 150）。命令示例：python .../extract_pdf_images.py <pdf路径> <输出目录> --min-size 120 [--manifest <manifest.md>]。
-xlsx：使用提供的 Claude xlsx 技能。
2.1 对于图片: 
-必须抽取：架构图、核心功能/模块图、官方路线图；
-建议抽取：市场/区域/财务/组织相关图；
-可选：一般配图、截图。
-不抽取: 图标, LOGO, 背景图片等.
-抽取的每个图片形成单独的文件(png格式优先,尽量保证图片的清晰度),记录包括图片所在的原始文档,页码,周边文字. 并记录到 manifest 中.
-图片 manifest 默认按「一个源文档一个文件」生成（如 浪潮竞品分析v0_7_images_manifest.md），理由：每个文档单独跑一次抽图脚本，脚本只处理一个输入、写一个清单即可，无需合并或加锁；且选图时能直接看出某图来自哪份材料。若希望 Step 3 选图时只读一个清单，可在 Step 2 完成后运行 merge_manifests.py 合并为单一 images_manifest.md。**网页链接**中的图片可通过 fetch_links.py 加 **--with-images --min-size 120** 抓取到 images/ 并生成 links_images_manifest.md，与文档 manifest 一并参与 merge_manifests 与选图；若目标站 HTTPS 证书过期或自签名，可加 **--insecure** 跳过证书校验（仅建议在可信环境使用）。
step 3. 根据 output_define.md 的要求，形成目标文档. 目标文档以中文为主，**版式与样式须符合 output_define.md 的文档风格定义**. 采用**两段式撰写**，避免在写 docx 时再次压缩内容：
-迭代1（两段式）. **【撰写前必须先通读全部抽取文本】** 写草稿前，必须先**逐一阅读** `extracted_content/<竞品名>/text/` 下的**全部** .md 文件（可结合 references 下该竞品的 docs_input.md 理解每份文档用途），不得只读 1～2 个文件或只读开头几段就动笔；与大纲某章节明显相关的段落必须读到并考虑是否写入草稿。**禁止敷衍阅读**：仅扫一眼目录或前几段即开始写，会导致内容单薄、遗漏来源，视为未达标。
-迭代1（两段式）续. **① 先写详细 markdown 草稿**：在完成上述通读后，按 output_define 的大纲与「内容与撰写要求」「各章节撰写要点」撰写**详细报告草稿**，保存为 `extracted_content/<竞品名>/report_draft.md`。草稿须充分引用已读文本中的要点、数据、案例；每节有要点、数据、案例或对比，可多用列表、子标题、表格；不必考虑 docx 版式。**② 再整理为 docx**：以 report_draft.md 为唯一正文来源，整理成目标 docx，应用 output_define 的字体、段落、标题层级与图/表注样式；**不得在整理时删减草稿中已有的要点**，仅做格式与段落组织。无材料的章节在草稿中即标 TODO，整理时保留。
-**长草稿分段生成（避免单次输出过长失败）**：若大模型单次输出整份 report_draft.md 易超长或中途失败，应采用分段生成，避免反复整篇重试。推荐做法：**① 按章节分段**：每次只写一个或若干小节（如「只写 2.1、2.2 两节」），每段生成后**立即追加**写入 report_draft.md，或先写入 `extracted_content/<竞品名>/sections/` 下的小节文件（建议文件名带序号以控制顺序，如 01_公司概况.md、02_1.1_行业位置.md），再运行 **merge_report_sections.py** 合并为 report_draft.md；**② 先出大纲再填内容**：可先让模型只输出报告大纲（一、二级标题），再按大纲逐条请求「只写第 X 章 / 只写 2.1 节」并追加；**③ 失败时断点续写**：若某段生成失败，不要清空重来，用「已写到这里：…，请从下一节继续」从断点续写并追加。最终需得到**一份完整**的 report_draft.md，再交给 md_to_report_docx.py 整理为 docx。
-迭代2. 【必须执行，不得省略】往目标文档中添加图片内容；**严禁仅凭 manifest 文字或文件名选图，否则会导致图文不匹配**。流程必须按以下顺序执行：
--① 先阅读 2.2 形成的图片 manifest，按原始文档、页码、周边文字初步筛选与报告章节相关的**候选图片**（不在此步决定最终放置）。
--② **【必须看图】** 对每一张候选图片，必须打开/查看图片内容（调用大模型看图或人工查看），根据**图片实际内容**判断：是否值得插入、应插入哪一章节、图注应写什么。图注必须与图片内容一致（如为架构图则写架构说明，为功能模块图则写模块说明），不得仅按 manifest 周边文字写图注。
--③ **【禁止用 LOGO/品牌图当内容图】** 公司 LOGO、品牌标识、纯图标不得作为「标准」「架构」「功能」「模块」等章节的说明图；若某节仅有此类图则宁可不插图，并在放置清单或自检中注明「本节无合适图」。
--④ 根据②的看图结果形成「图片放置清单」（heading、image 路径、caption），再使用 insert_report_images.py 插入。插入后建议人工抽查 docx，确认每张图所在章节与图注是否与该图内容一致。
-**选图覆盖与数量要求**（不得应付了事）：须**按章节类型系统选图**，而非随便选 2 张。至少应覆盖以下四类章节（若 manifest 中有经看图确认合适的图）：**1.4 产品组合**（产品版图/布局类）、**2.1 架构&技术分析**（架构图/技术栈类）、**2.2 功能分析**（功能模块/开通·保障·资源类）、**2.9 标准&规范遵循**（标准/规范类）。每类在 manifest 有合适图时至少选 1 张；若某类在 manifest 中无合适图（如全是 LOGO/图标），可不选，但须在放置清单或自检中注明「本节无合适图」。**禁止**为省事只选 2 张或只覆盖 1～2 类章节。
-**避免图文不匹配**：若仅凭 manifest 选图而未看图，极易出现（1）图与章节不符（如把非架构图放在「架构&技术分析」）、（2）图注与图片内容不符（如把公司 LOGO 配图注「遵循的电信标准」）。因此②的看图步骤不可省略或替代。
-Step 3 完成标准：① 迭代1 已完成（**已通读** text/ 下全部 .md 后再写草稿，目标 docx 包含 output_define 要求的全部章节文字且内容有据可查）；② 迭代2 已完成（已阅读 manifest、**经看图**确定每张图的章节与图注，**选图覆盖满足上述四类要求**，插入后建议人工抽查图文一致）。两项均满足后，报告方可视为完成。

## 调用约定
- **强制**：所有脚本均在项目根目录下执行，且**必须先**激活项目虚拟环境（Windows: `.venv\Scripts\Activate.ps1`；Linux/macOS: `source .venv/bin/activate`）。未激活虚拟环境时 run_markitdown 等可能因依赖冲突而失败。
- 脚本路径为 <技能目录>/scripts/<脚本名>.py。
docx、pptx 转 markdown 统一用 run_markitdown.py（不依赖系统 pandoc；Python 3.13+ 下可避免 aifc 报错）。勿直接使用 python -m markitdown。
- 字符集**必须使用**utf-8
- 执行命令时, windows平台**必须使用**powershell语法.

## Step 与脚本对应
| 步骤 | 脚本 | 必填参数 | 常用可选 | 输出/用途 |
|------|------|----------|----------|-----------|
| Step 2 开始前 | prepare_extraction.py | --ref-dir（竞品目录） | --output-base .（默认当前目录） | 创建 extracted_content/<竞品>/ 与 worklist.json；按 worklist 的 documents 逐条用对应方式抽取 |
| Step 2 批量抽取（可选） | run_extraction.py | --worklist 或 --extracted-dir | --min-size 120 | 按 worklist 批量执行 run_markitdown + extract_*_images，一次完成文字与图片抽取 |
| docx/pptx/pdf 转 markdown（Step 2 中） | run_markitdown.py | 文档路径 | -o <输出.md> | 将 docx、pptx 或 pdf 转为 markdown，无需 pandoc |
| DOCX 图片抽取（Step 2 中） | extract_docx_images.py | docx路径、输出目录 | --min-size 120、--manifest <路径> | 从 DOCX 抽取内嵌图片并生成 manifest（序号、所在段落文字） |
| PPTX 图片抽取（Step 2 中） | extract_pptx_images.py | pptx路径、输出目录 | --min-size 120、--manifest <路径> | 从 PPTX 抽取内嵌图片并生成 manifest（幻灯片号、该页原文摘要） |
| PDF 图片抽取（Step 2 中） | extract_pdf_images.py | pdf路径、输出目录 | --min-size 120、--manifest <路径> | 从 PDF 抽取内嵌图片；--min-size 120 过滤小图（LOGO/图标） |
| 需网页时（Step 2 中） | fetch_links.py | --output-dir（如 extracted_content/Inspur/links） | --worklist 或 --ref-dir；--with-images --min-size 120 同时抓网页内图片并生成 links_images_manifest.md；目标站证书异常时加 --insecure 跳过 HTTPS 校验 | 生成 links/ 与 links_index.md；加 --with-images 时另生成 images/ 与 links_images_manifest.md，可与 merge_manifests 合并 |
| 用户只给竞品名/别名时 | resolve_competitor.py | --competitor | --print-dir-only | 得到 --ref-dir，作为 prepare_extraction 的 --ref-dir |
| Step 3 写 docx 前 | report_stub.py | --competitor | --reports-root . --print-path-only --avoid-overwrite | 得到报告完整路径，用于写入 docx |
| Step 3 迭代1（草稿→docx） | md_to_report_docx.py | --competitor | --draft、--out、--reports-root | 从 report_draft.md 生成符合 output_define 样式的 docx，不删减草稿要点 |
| Step 3 迭代1（分段合并） | merge_report_sections.py | --sections-dir 或 --extracted-dir | --output | 将 sections/ 下小节 .md 按文件名顺序合并为 report_draft.md |
| Step 3 迭代2（必须） | insert_report_images.py | docx路径、放置清单JSON | 无 | 按放置清单将图片插入 docx 对应章节并加图注 |
| Step 2 完成后（可选） | validate_manifest.py | --extracted-dir（如 extracted_content/Inspur） | --report <路径> | 校验 images/ 与 manifest 是否一致 |
| Step 2 完成后（可选） | merge_manifests.py | --extracted-dir | 无 | 将各文档的 manifest 合并为单一 images_manifest.md，便于 Step 3 选图时一次阅读 |
## 串联示例（竞品名 Inspur，项目根为 .）
0. **激活虚拟环境**（必须）：在项目根执行 `.venv\Scripts\Activate.ps1`（Windows）或 `source .venv/bin/activate`（Linux/macOS），后续所有 `python` 命令均在此 shell 中执行。
1. 若只有竞品名：先运行 resolve_competitor --competitor Inspur --print-dir-only，将输出作为 ref_dir。
2. 运行 prepare_extraction --ref-dir <ref_dir> --output-base . ；得到 worklist.json。
3. 抽取内容：在已激活虚拟环境的 shell 中调用 run_extraction.py --worklist extracted_content/Inspur/worklist.json 一次性完成所有文档的 run_markitdown + 抽图；或按 worklist 逐条手动执行 run_markitdown 与 extract_*_images。xlsx 用 Claude xlsx 技能。结果写入 extracted_root 下的 text/、images/，并维护图片 manifest。
4. 若 worklist 的 links 非空：运行 fetch_links --worklist extracted_content/Inspur/worklist.json --output-dir extracted_content/Inspur/links（需同时抓网页内图片时加 --with-images --min-size 120；目标站证书过期或自签名时加 --insecure）；后续只读 links_index.md 与 links/*.html，若有 links_images_manifest.md 可参与 merge_manifests 与 Step 3 选图。
5. 可选：validate_manifest --extracted-dir extracted_content/Inspur。
6. Step 3 迭代1（两段式）：① **先通读** extracted_content/<竞品>/text/ 下**全部** .md 文件（可结合 docs_input.md），不得只读 1～2 个文件或只读开头就动笔。② 再写 **report_draft.md** 到 extracted_content/<竞品>/report_draft.md，按「内容与撰写要求」与「各章节撰写要点」充分展开，每节有要点/数据/案例/对比，可列表表格；若采用分段撰写，可先写小节到 extracted_content/<竞品>/sections/（文件名建议带序号如 01_公司概况.md），再运行 **merge_report_sections.py --extracted-dir extracted_content/Inspur** 合并为 report_draft.md。③ 运行 **md_to_report_docx.py** 从草稿生成目标 docx（如 `python .../md_to_report_docx.py --competitor Inspur`），输出为 reports/<竞品>_v1.0_<日期>.docx；不删减草稿要点，仅应用 output_define 的文档风格（标题层级、首行缩进、字体字号等）。
7. Step 3 迭代2（必须）：① 阅读 manifest 初选候选图（可先 merge_manifests 便于一次看全）。② **必须看图**：对每张候选图查看其实际内容，据此决定是否插入、插入哪一章、图注写什么（图注须与图片内容一致）；禁止用公司 LOGO/品牌图充当标准、架构、功能等说明图。③ **按四类章节系统选图**：至少覆盖 1.4 产品组合、2.1 架构、2.2 功能、2.9 标准（manifest 有合适图时每类至少 1 张）；不得只选 2 张应付。④ 编写图片放置清单，运行 insert_report_images.py 插入；插入后建议人工抽查 docx 确认图文一致。
