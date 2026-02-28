# 说明
这是一个竞品分析技能. 适用产品经理.

# 安装
## 在cursor中安装
1. 打开cursor
2. File->Open Folder, 打开一个文件夹. (推荐使用一个空文件夹)
3. 创建 .cursor/skills目录
4. 将本技能复制到.cursor/skills目录中
5. 在当前项目目录下安装python3虚拟环境
6. 安装python依赖 pip install -r requirements.txt

## 在Openclaw中安装
1. 进入<user home>/.openclaw/skills/
2. 将本技能复制到.openclaw/skills/目录中
3. 在技能目录下安装python3虚拟环境
4. 安装python依赖 pip install -r requirements.txt

## 使用
1. 在技能的references目录下创建竞品子目录, 推荐英文名
2. 如果该竞品有一些别名，请编辑alias.md文件, 格式为竞品名 别名(可以有多个，空格分隔)
3. 在竞品子目录下放置竞品分析素材文件，格式包括pptx, docx, pdf, xlsx等
4. 在竞品子目录下创建docs_input.md文件, 格式为文件名 文件描述
5. 可选: 在竞品子目录下创建links_input.md文件, 格式为URL URL描述
6. 在对话框中输入：###竞品分析
7. 完成后，在reports目录下会生成竞品分析报告。文件名为: <竞品>_v1.0_yyyymmdd.docx. reports目录位于项目目录(cursor)或者技能目录(openclaw).

## 技能处理过程
1. 技能首先会将本地素材文件提取为markdown文件和对应的图片文件。如果links_input.md文件存在，技能会从对应的URL爬取文字和图片.
2. 技能阅读output_define.md，理解输出要求
3. 技能阅读抽取的md文件，按输出要求生成报告的文字版本
4. 技能分析图片，从中选择一些重要的图片，更新上一步的文字版本，形成最终的图文版本.
