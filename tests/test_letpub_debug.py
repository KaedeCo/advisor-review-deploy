"""调试版 LetPub runner — 输出详细诊断信息"""
import sys
import os
import json
import time
from pathlib import Path

# 读取 PHPSESSID
config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
PHPSESSID = config.get("cookies", {}).get("letpub", "").strip()
print(f"[DEBUG] PHPSESSID: {PHPSESSID[:20]}...{PHPSESSID[-8:]}" if len(PHPSESSID) > 28 else f"[DEBUG] PHPSESSID: {PHPSESSID}")

from playwright.sync_api import sync_playwright

ADVISOR = "刘玉身"
UNIVERSITY = "清华大学"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(
        locale="zh-CN",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    )

    if PHPSESSID:
        ctx.add_cookies([{
            "name": "PHPSESSID", "value": PHPSESSID,
            "domain": "www.letpub.com.cn", "path": "/",
        }])
        print("[DEBUG] Cookie 已注入")

    page = ctx.new_page()

    # 1. 访问搜索页
    print("\n[1] 访问搜索页...")
    page.goto("https://www.letpub.com.cn/index.php?page=grant",
              wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    print(f"   URL: {page.url}")
    print(f"   Title: {page.title()}")

    # 2. 检查登录状态
    print("\n[2] 检查登录状态...")
    login_status = page.evaluate("""() => {
        const text = document.body.innerText;
        const hasLogin = text.indexOf('请先登录') >= 0 || text.indexOf('您尚未登录') >= 0;
        const hasLogout = text.indexOf('退出') >= 0;
        const hasUserInfo = text.indexOf('个人中心') >= 0 || text.indexOf('会员') >= 0;
        return {hasLogin, hasLogout, hasUserInfo, snippet: text.substring(0, 500)};
    }""")
    print(f"   需要登录: {login_status['hasLogin']}")
    print(f"   有退出按钮: {login_status['hasLogout']}")
    print(f"   有用户信息: {login_status['hasUserInfo']}")

    # 3. 关闭弹窗
    page.evaluate("""() => {
        document.querySelectorAll('.layui-layer-shade, .letpub_popup_notify_window').forEach(s => s.remove());
        document.querySelectorAll('.layui-layer-close').forEach(c => c.click());
    }""")
    time.sleep(0.5)

    # 4. 检查表单字段
    print("\n[3] 检查搜索表单...")
    form_info = page.evaluate("""() => {
        var form = document.querySelector('#searchform_advanced');
        if (!form) return {error: 'no form found'};
        var person = form.querySelector('input[name="person"]');
        var startTime = form.querySelector('select[name="startTime"]');
        var endTime = form.querySelector('select[name="endTime"]');
        return {
            personExists: !!person,
            startTimeOptions: startTime ? startTime.options.length : 0,
            startTimeFirst: startTime ? startTime.options[0].value : '',
            startTimeLast: startTime ? startTime.options[startTime.options.length-1].value : '',
            endTimeOptions: endTime ? endTime.options.length : 0,
            endTimeFirst: endTime ? endTime.options[0].value : '',
            endTimeLast: endTime ? endTime.options[endTime.options.length-1].value : '',
        };
    }""")
    print(f"   表单信息: {form_info}")

    # 5. 填入表单 + 设置年份范围
    print(f"\n[4] 填入表单: person={ADVISOR}, company={UNIVERSITY}")
    page.evaluate("""
    (data) => {
        var form = document.querySelector('#searchform_advanced');
        form.querySelector('input[name="person"]').value = data.name;
        if (data.univ) form.querySelector('input[name="company"]').value = data.univ;

        var startTime = form.querySelector('select[name="startTime"]');
        var endTime = form.querySelector('select[name="endTime"]');
        if (startTime && startTime.options.length > 0) {
            startTime.selectedIndex = startTime.options.length - 1;
        }
        if (endTime && endTime.options.length > 0) {
            endTime.selectedIndex = 0;
        }
    }
    """, {"name": ADVISOR, "univ": UNIVERSITY})

    # 验证表单值
    form_values = page.evaluate("""() => {
        var form = document.querySelector('#searchform_advanced');
        return {
            person: form.querySelector('input[name="person"]').value,
            company: form.querySelector('input[name="company"]').value,
            startTime: form.querySelector('select[name="startTime"]').value,
            endTime: form.querySelector('select[name="endTime"]').value,
        };
    }""")
    print(f"   表单值: {form_values}")

    # 6. 触发搜索
    print("\n[5] 触发 checksubmit('advanced', 'list', 1)...")
    page.evaluate("""() => {
        if (typeof checksubmit === 'function') {
            checksubmit('advanced', 'list', 1);
        } else {
            console.log('checksubmit not found');
        }
    }""")
    time.sleep(5)

    # 7. 检查结果
    print("\n[6] 检查搜索结果...")
    result_info = page.evaluate("""() => {
        var table = document.getElementById('keyword-datalist');
        if (!table) return {tableExists: false};
        var rows = table.querySelectorAll('tbody tr');
        var cells = table.querySelectorAll('tbody tr td');
        var bodyText = table.querySelector('tbody') ? table.querySelector('tbody').innerText.substring(0, 300) : '';
        return {
            tableExists: true,
            rowCount: rows.length,
            cellCount: cells.length,
            bodyText: bodyText,
        };
    }""")
    print(f"   表格存在: {result_info.get('tableExists')}")
    print(f"   行数: {result_info.get('rowCount', 0)}")
    print(f"   单元格数: {result_info.get('cellCount', 0)}")
    if result_info.get('bodyText'):
        print(f"   表格内容: {result_info['bodyText'][:200]}")

    # 8. 检查页面是否有错误提示或登录弹窗
    print("\n[7] 检查错误/弹窗...")
    page_errors = page.evaluate("""() => {
        var alerts = document.querySelectorAll('.layui-layer-content, .alert, .error, [class*="error"], [class*="warning"]');
        var messages = [];
        alerts.forEach(a => {
            var t = a.innerText.trim();
            if (t && t.length > 5) messages.push(t.substring(0, 200));
        });
        // 检查是否有登录提示
        var bodyText = document.body.innerText;
        var loginPrompt = '';
        if (bodyText.indexOf('请先登录') >= 0) loginPrompt = '请先登录';
        if (bodyText.indexOf('您尚未登录') >= 0) loginPrompt = '您尚未登录';
        if (bodyText.indexOf('登录超时') >= 0) loginPrompt = '登录超时';
        return {messages: messages, loginPrompt: loginPrompt};
    }""")
    print(f"   登录提示: {page_errors.get('loginPrompt', '无')}")
    for msg in page_errors.get('messages', []):
        print(f"   弹窗: {msg[:150]}")

    # 9. 截图保存
    screenshot_path = os.path.join(os.path.dirname(__file__), "letpub_debug.png")
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"\n[8] 截图已保存: {screenshot_path}")

    # 10. 获取页面 URL（检查是否被重定向到登录页）
    print(f"\n[9] 当前 URL: {page.url}")

    ctx.close()
    browser.close()
    print("\n调试完成")
