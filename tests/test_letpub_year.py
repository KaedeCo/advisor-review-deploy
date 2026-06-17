"""检查 LetPub 搜索表单的年份选择器结构"""
import sys, json
sys.path.insert(0, '.')

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.letpub.com.cn/index.php?page=grant", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # 找所有 select 和年份相关的 input
    selects = page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('select').forEach(s => {
            result.push({
                name: s.name || '',
                id: s.id || '',
                options: Array.from(s.options).slice(0, 5).map(o => o.value + ':' + o.text),
                optionCount: s.options.length
            });
        });
        return result;
    }""")

    print("All selects on page:")
    for s in selects:
        print(f"  name={s['name']} id={s['id']} options={s['optionCount']}")
        for o in s['options'][:3]:
            print(f"    {o}")

    # 找年份相关的 input
    year_inputs = page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('input').forEach(i => {
            if (i.name && (i.name.indexOf('year') >= 0 || i.name.indexOf('start') >= 0 || i.name.indexOf('end') >= 0)) {
                result.push({name: i.name, id: i.id, type: i.type, value: i.value, placeholder: i.placeholder});
            }
        });
        return result;
    }""")
    print("\nYear-related inputs:")
    for i in year_inputs:
        print(f"  {i}")

    # 找搜索表单的所有字段
    form_fields = page.evaluate("""() => {
        const form = document.querySelector('#searchform_advanced') || document.querySelector('form');
        if (!form) return [];
        return Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
            tag: el.tagName,
            name: el.name || '',
            id: el.id || '',
            type: el.type || '',
            value: (el.value || '').substring(0, 30)
        }));
    }""")
    print("\nForm fields:")
    for f in form_fields:
        print(f"  {f['tag']:6s} name={f['name']:15s} id={f['id']:15s} type={f['type']:10s} value={f['value']}")

    browser.close()
