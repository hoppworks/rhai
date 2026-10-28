import subprocess,json,time,sys
mapping={' ':'spc','\n':'ret',';':'semicolon',':':'semicolon','-':'minus','_':'minus','.':'dot',',':'comma','/':'slash','\\':'backslash',"'":'apostrophe','"':'apostrophe','(':'9',')':'0','[':'bracket_left',']':'bracket_right','{':'bracket_left','}':'bracket_right','|':'backslash','$':'4','=':'equal','+':'equal','&':'7','!':'1','#':'3','%':'5','*':'8','?':'slash','<':'comma','>':'dot','@':'2','^':'6','~':'grave_accent','`':'grave_accent'}
shift=set(':_"(){}|$+&!#%*?<>@^~')
def event(k,d):return {'type':'key','data':{'down':d,'key':{'type':'qcode','data':k}}}
def send(events):
 p=subprocess.run(['virsh','qemu-monitor-command','rhai-win11-quality',json.dumps({'execute':'input-send-event','arguments':{'events':events}})],capture_output=True,text=True,check=True,timeout=5)
 assert 'error' not in p.stdout,p.stdout
for c in sys.argv[1]:
 k=mapping.get(c,c.lower());sh=c in shift or c.isupper()
 if sh:send([event('shift',True)]);time.sleep(.035)
 send([event(k,True)]);time.sleep(.035);send([event(k,False)]);time.sleep(.035)
 if sh:send([event('shift',False)]);time.sleep(.035)
print('paced command delivered')
