---
description: 起看板服务并打开浏览器
---
!`python runtime/daemon.py 8790 2>&1 | tail -2`

!`python runtime/board_sync.py 2>&1 | tail -1`

看板地址（端口以 `runtime/.port` 为准，缺省固定 8790）：

!`printf 'http://127.0.0.1:%s\n' "$(cat runtime/.port 2>/dev/null || echo 8790)"`

请把上面的地址给用户，并提醒：**不要**双击 `runtime/ui/index.html` 本地打开
（`file://` 下没有后端，页面永远是死的空板）。
