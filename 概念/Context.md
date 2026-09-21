---
tags: [概念, AI-Agent]
---

# Context(上下文)與 Context Window

**Context**:LLM 這一次回答時,能同時「看到」的所有內容,包含 System Prompt、對話歷史、檢索到的資料、使用者這次的問題。

**Context Window(上下文長度)**:context 的上限,以 **token** 計算。超過時,最舊的內容會被擠掉,模型等於「忘記」。

## 關鍵觀念
LLM 本身沒有記憶。每一輪對話都是把前面的紀錄**重新塞進 context** 再送給模型,看起來才像有記憶。

## 在課程中的位置
- 單元 1:Context Window 是 [[LLM]] 的參數之一
- 單元 3:context of round(對話輪數)是 [[Memory]] 的第一種類型
- 單元 4:[[Knowledge與RAG]] 把檢索結果放進 context

屬於 [[AI Agent]]
