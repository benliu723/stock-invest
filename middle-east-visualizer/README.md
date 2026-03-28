# Middle East Visualizer

本地单页可视化，用于把 `middle-east-war-trend` 的文本输出转换为历史概率图和信息层重点事件时间线。

## Usage

```bash
npm install
npm run ingest
npm run dev
```

默认会读取 `data/raw/*.md`，把解析后的 dataset 写到 `public/data/dataset.json`。

## Capture Current Report

把本次分析结果直接保存到 raw store：

```bash
cd /Users/benliu/Documents/Playground/middle-east-visualizer
pbpaste | npm run sync-report -- --label "今日中东局势分析"
```

然后打开 [http://localhost:4173](http://localhost:4173)。
