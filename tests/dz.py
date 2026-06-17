"""逐步调试"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'backend')
from app.services.crawlers.daoshipingjia import DaoshiPingjiaScraper

s = DaoshiPingjiaScraper()

# Step 1
print("Step1: 匹配学校 清华大学")
url = s._match_school("清华大学")
print(f"  URL: {url}")

# Step 2
print("\nStep2: 匹配院系 计算机")
dept = s._match_department(url, "计算机")
print(f"  院系URL: {dept}")

# Step 3
print("\nStep3: 匹配导师 孙立峰")
advs = s._match_advisors(dept, "孙立峰")
print(f"  导师: {len(advs)} 位")
for a in advs:
    print(f"    name={a['name'][:30]} tid={a['teacher_id']} score={a['score']}")
