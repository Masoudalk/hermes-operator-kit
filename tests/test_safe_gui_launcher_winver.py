import sys
import psutil

sys.path.insert(0, 'C:/agent-work/lib')
from safe_gui_launcher import launch_app_safely, _is_process_running

APP = 'WindowsVersion'
EXE = 'C:/Windows/System32/winver.exe'

if _is_process_running('winver.exe'):
    print('PRECONDITION_FAIL=winver already running')
    sys.exit(2)

ok1, msg1 = launch_app_safely(APP, EXE)
ok2, msg2 = launch_app_safely(APP, EXE)

pids = []
for p in psutil.process_iter(['pid', 'name']):
    try:
        if p.info['name'] and p.info['name'].lower() == 'winver.exe':
            pids.append(p.info['pid'])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print('FIRST_OK=' + str(ok1))
print('SECOND_OK=' + str(ok2))
print('FIRST_MSG=' + msg1)
print('SECOND_MSG=' + msg2)
print('WINVER_PIDS=' + ','.join(map(str, pids)))

if ok1 is True and ok2 is False and len(pids) == 1:
    print('RESULT=PASS')
    sys.exit(0)

print('RESULT=FAIL')
sys.exit(1)