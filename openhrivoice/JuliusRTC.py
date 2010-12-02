#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Julius speech recognition component

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import sys, os, socket, subprocess, signal, threading, platform
import time, struct, traceback, locale, codecs, getopt, wave, tempfile
from glob import glob
from BeautifulSoup import BeautifulSoup
from xml.dom.minidom import Document
from parsesrgs import *
import OpenRTM_aist
import RTC

class JuliusWrap(threading.Thread):
    CB_DOCUMENT = 1
    CB_LOGWAVE = 2
    
    def __init__(self, language='jp'):
        threading.Thread.__init__(self)
        self._running = False
        self._platform = platform.system()
        self._gotinput = False
        self._lang = language
        self._memsize = "large"
        #self._memsize = "medium"
        self._logdir = tempfile.mkdtemp()
        self._callbacks = []
        self._grammars = {}
        self._firstgrammar = True
        self._activegrammars = {}
        self._prevdata = ''
        if hasattr(sys, "frozen"):
            self._basedir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        else:
            self._basedir = os.path.dirname(__file__)
        self._modulesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._audiosocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._cmdline = []
        if self._platform == "Windows":
            self._cmdline.append(os.path.join(self._basedir, "3rdparty", "dictation-kit-v4.0-win\\bin\\julius.exe"))
            if self._lang == 'jp':
                self._cmdline.extend(['-h',  os.path.join(self._basedir, "3rdparty", "dictation-kit-v4.0-win\\model\\phone_m\\hmmdefs_ptm_gid.binhmm")])
                self._cmdline.extend(['-hlist', os.path.join(self._basedir, "3rdparty", "dictation-kit-v4.0-win\\model\\phone_m\\logicalTri")])
                self._cmdline.extend(["-dfa", os.path.join(self._basedir, "dummy.dfa")])
                self._cmdline.extend(["-v" , os.path.join(self._basedir, "dummy.dict")])
                self._cmdline.extend(["-sb", "80.0"])
            else:
                self._cmdline.extend(['-h', os.path.join(self._basedir, "3rdparty", "julius-voxforge-build726\\hmmdefs")])
                self._cmdline.extend(['-hlist', os.path.join(self._basedir, "3rdparty", "julius-voxforge-build726\\tiedlist")])
                self._cmdline.extend(["-dfa", os.path.join(self._basedir, "dummy-en.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._basedir, "dummy-en.dict")])
                self._cmdline.extend(["-sb", "160.0"])
        else:
            self._cmdline.append("/usr/bin/julius")
            if self._lang == 'jp':
                self._cmdline.extend(["-h", "/usr/share/julius-runkit/model/phone_m/hmmdefs_ptm_gid.binhmm"])
                self._cmdline.extend(["-hlist", "/usr/share/julius-runkit/model/phone_m/logicalTri"])
                self._cmdline.extend(["-dfa", os.path.join(self._basedir, "dummy.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._basedir, "dummy.dict")])
                #self._cmdline += " -d /usr/share/julius-runkit/model/lang_m/web.60k.8-8.bingramv4.gz"
                #self._cmdline += " -v /usr/share/julius-runkit/model/lang_m/web.60k.htkdic"
                self._cmdline.extend(["-sb", "80.0"])
            elif self._lang == 'de':
                self._cmdline.extend(["-h", "/usr/share/julius-voxforge-de/acoustic/hmmdefs"])
                self._cmdline.extend(["-hlist", "/usr/share/julius-voxforge-de/acoustic/tiedlist"])
                self._cmdline.extend(["-dfa", os.path.join(self._basedir, "dummy-en.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._basedir, "dummy-en.dict")])
                self._cmdline.extend(["-sb", "120.0"])
            else:
                self._cmdline.extend(["-h", "/usr/share/julius-voxforge/acoustic/hmmdefs"])
                self._cmdline.extend(["-hlist", "/usr/share/julius-voxforge/acoustic/tiedlist"])
                self._cmdline.extend(["-dfa", os.path.join(self._basedir, "dummy-en.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._basedir, "dummy-en.dict")])
                self._cmdline.extend(["-sb", "160.0"])
        self._audioport = self.getunusedport()
        self._moduleport = self.getunusedport()
        self._cmdline.extend(["-input", "adinnet",  "-adport",  str(self._audioport)])
        self._cmdline.extend(["-module", str(self._moduleport)])
        if self._memsize == "large":
            self._cmdline.extend(["-b", "-1", "-b2", "120", "-s", "1000" ,"-m", "2000"])
        else:
            self._cmdline.extend(["-b", "-1", "-b2", "80", "-s", "500" ,"-m", "1000"])
        self._cmdline.extend(["-n", "5", "-output", "5"])
        self._cmdline.extend(["-pausesegment", "-rejectshort", "200"])
        #self._cmdline.extend(["-multipath"])
        self._cmdline.extend(["-spmodel", "sp", "-iwsp", "-iwsppenalty", "-70.0"])
        self._cmdline.extend(["-penalty1", "5.0", "-penalty2", "20.0", "-iwcd1", "max", "-gprune", "safe"])
        self._cmdline.extend(["-record", self._logdir])
        self._cmdline.extend(["-smpFreq", "16000"])
        self._cmdline.extend(["-forcedict"])
        print "command line: %s" % " ".join(self._cmdline)
        self._running = True
        self._p = subprocess.Popen(self._cmdline)
        print "connecting to ports"
        for retry in range(0, 10):
            try:
                self._modulesocket.connect(("localhost", self._moduleport))
            except socket.error:
                time.sleep(1)
                continue
            break
        for retry in range(0, 10):
            try:
                self._audiosocket.connect(("localhost", self._audioport))
            except socket.error:
                time.sleep(1)
                continue
            break
        self._modulesocket.sendall("INPUTONCHANGE TERMINATE\n")
        print "JuliusWrap started"

    def getunusedport(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, port = s.getsockname()
        s.close()
        return port

    def terminate(self):
        print 'JuliusWrap: terminate'
        self._running = False
        self._audiosocket.close()
        self._modulesocket.close()
        self._p.terminate()
        return 0

    def write(self, data):
        try:
            self._audiosocket.send(struct.pack("i", len(data)))
            self._audiosocket.sendall(data)
        except socket.error:
            try:
                self._audiosocket.connect(("localhost", self._audioport))
            except:
                pass
        return 0

    def run(self):
        while self._running:
            for f in glob(os.path.join(self._logdir, "*.wav")):
                for c in self._callbacks:
                    c(self.CB_LOGWAVE, f)
            try:
                self._modulesocket.settimeout(1)
                data = self._prevdata + unicode(self._modulesocket.recv(1024*10), 'euc_jp')
            except socket.timeout:
                continue
            except socket.error:
                print 'socket error'
                break
            self._gotinput = True
            ds = data.split(".\n")
            self._prevdata = ds[-1]
            ds = ds[0:-1]
            for d in ds:
                dx = BeautifulSoup(d)
                for c in self._callbacks:
                    c(self.CB_DOCUMENT, dx)
        print 'JuliusWrap: exit from event loop'

    def addgrammar(self, data, name):
        if self._firstgrammar == True:
            self._modulesocket.sendall("CHANGEGRAM %s\n" % (name,))
            self._firstgrammar = False
        else:
            self._modulesocket.sendall("ADDGRAM %s\n" % (name,))
        self._modulesocket.sendall(data.encode('euc_jp', 'backslashreplace'))
        self._grammars[name] = len(self._grammars)
        self._activegrammars[name] = True
        time.sleep(0.1)

    def activategrammar(self, name):
        try:
            gid = self._grammars[name]
        except KeyError:
            print "[error] unknown grammar: %s" % (name,)
            return
        print "ACTIVATEGRAM %s" % (name,)
        self._modulesocket.sendall("ACTIVATEGRAM\n%s\n" % (name,))
        self._activegrammars[name] = True
        time.sleep(0.1)

    def deactivategrammar(self, name):
        try:
            gid = self._grammars[name]
        except KeyError:
            print "[error] unknown grammar: %s" % (name,)
            return
        print "DEACTIVATEGRAM %s" % (name,)
        self._modulesocket.sendall("DEACTIVATEGRAM\n%s\n" % (name,))
        del self._activegrammars[name]
        time.sleep(0.1)

    def syncgrammar(self):
        self._modulesocket.sendall("SYNCGRAM\n")

    def switchgrammar(self, name):
        self.activategrammar(name)
        for g in self._activegrammars.keys():
            if g != name:
                self.deactivategrammar(g)

    def setcallback(self, func):
        self._callbacks.append(func)

JuliusRTC_spec = ["implementation_id", "JuliusRTC",
                  "type_name",         "JuliusRTC",
                  "description",       "Julius speech recognition component (python implementation)",
                  "version",           "1.0.0",
                  "vendor",            "AIST",
                  "category",          "communication",
                  "activity_type",     "DataFlowComponent",
                  "max_instance",      "10",
                  "language",          "Python",
                  "lang_type",         "script",
                  "conf.default.language", "japanese",
                  "conf.__widget__.language", "radio",
                  "conf.__constraints__.language", "(japanese, english, german)",
                  "conf.default.phonemodel", "male",
                  "conf.__widget__.phonemodel", "radio",
                  "conf.__constraints__.phonemodel", "(male)",
                  "conf.default.voiceactivitydetection", "internal",
                  "conf.__widget__.voiceactivitydetection", "radio",
                  "conf.__constraints__.voiceactivitydetection", "(internal)",
                  ""]

class DataListener(OpenRTM_aist.ConnectorDataListenerT):
    def __init__(self, name, obj, dtype):
        self._name = name
        self._obj = obj
        self._dtype = dtype
    
    def __call__(self, info, cdrdata):
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self, info, cdrdata, self._dtype(RTC.Time(0,0),None))
        self._obj.onData(self._name, data)


class JuliusRTC(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)

    def onInitialize(self):
        try:
            self._lang = 'en'
            self._srgs = None
            self._j = None
            # create inport for audio stream
            self._indata = RTC.TimedOctetSeq(RTC.Time(0,0), None)
            self._inport = OpenRTM_aist.InPort("data", self._indata)
            self._inport.addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                                  DataListener("data", self, RTC.TimedOctetSeq))
            self.registerInPort("data", self._inport)
            # create inport for active grammar
            self._grammardata = RTC.TimedString(RTC.Time(0,0), "")
            self._grammarport = OpenRTM_aist.InPort("activegrammar", self._grammardata)
            self._grammarport.addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                                       DataListener("activegrammar", self, RTC.TimedString))
            self.registerInPort("activegrammar", self._grammarport)
            # create outport for status
            self._statusdata = RTC.TimedString(RTC.Time(0,0), "")
            self._statusport = OpenRTM_aist.OutPort("status", self._statusdata)
            self.registerOutPort("status", self._statusport)
            # create outport for result
            self._outdata = RTC.TimedString(RTC.Time(0,0), "")
            self._outport = OpenRTM_aist.OutPort("result", self._outdata)
            self.registerOutPort("result", self._outport)
            # create outport for log
            self._logdata = RTC.TimedOctetSeq(RTC.Time(0,0), None)
            self._logport = OpenRTM_aist.OutPort("log", self._logdata)
            self.registerOutPort("log", self._logport)
        except:
            traceback.print_exc()
        return RTC.RTC_OK

    def onActivated(self, ec_id):
        try:
            self._lang = self._srgs._lang
            self._j = JuliusWrap(self._lang)
            self._j.start()
            self._j.setcallback(self.onResult)
            while self._j._gotinput == False:
                time.sleep(0.1)
            for r in self._srgs._rules.keys():
                gram = self._srgs.toJulius(r)
                print "register grammar: %s" % (r,)
                print gram
                self._j.addgrammar(gram, r)
            self._j.switchgrammar(self._srgs._rootrule)
        except:
            traceback.print_exc()
        return RTC.RTC_OK

    def onData(self, name, data):
        try:
            if self._j:
                if name == "data":
                    self._j.write(data.data)
                elif name == "activegrammar":
                    self._j.switchgrammar(data.data)
        except:
            print traceback.format_exc()

    def onExecute(self, ec_id):
        time.sleep(1)
        return RTC.RTC_OK

    def onDeactivate(self, ec_id):
        if self._j:
            self._j.terminate()
            self._j.join()
            self._j = None
        return RTC.RTC_OK

    def onFinalize(self):
        if self._j:
            self._j.terminate()
            self._j.join()
            self._j = None
        return RTC.RTC_OK

    def onResult(self, type, data):
        if type == JuliusWrap.CB_DOCUMENT:
            d = data.first()
            if d.name == 'input':
                print d['status']
                self._statusdata.data = str(d['status'])
                self._statusport.write()
            elif d.name == 'rejected':
                print 'rejected'
                self._statusdata.data = 'rejected'
                self._statusport.write()
            elif d.name == 'recogout':
                doc = Document()
                listentext = doc.createElement("listenText")
                doc.appendChild(listentext)
                for s in d.findAll('shypo'):
                    hypo = doc.createElement("data")
                    score = 0
                    count = 0
                    text = []
                    for w in s.findAll('whypo'):
                        if w['word'][0] == '<':
                            continue
                        whypo = doc.createElement("word")
                        whypo.setAttribute("text", w['word'])
                        whypo.setAttribute("score", w['cm'])
                        hypo.appendChild(whypo)
                        text.append(w['word'])
                        score += float(w['cm'])
                        count += 1
                    if count == 0:
                        score = 0
                    else:
                        score = score / count
                    hypo.setAttribute("rank", s['rank'])
                    hypo.setAttribute("score", str(score))
                    hypo.setAttribute("likelihood", s['score'])
                    hypo.setAttribute("text", " ".join(text))
                    listentext.appendChild(hypo)
                data = doc.toxml(encoding="utf-8")
                print data.decode('utf-8', 'backslashreplace')
                self._outdata.data = data
                self._outport.write()
        elif type == JuliusWrap.CB_LOGWAVE:
            t = os.stat(data).st_ctime
            tf = t - int(t)
            self._logdata.tm = RTC.Time(int(t - tf), int(tf * 1000000000))
            try:
                wf = wave.open(data, 'rb')
                self._logdata.data = wf.readframes(wf.getnframes())
                wf.close()
                os.remove(data)
                self._logport.write()
            except:
                pass

    def setgrammar(self, srgs):
        self._srgs = srgs

class JuliusRTCManager:
    def __init__(self):
        try:
            opts, args = getopt.getopt(sys.argv[1:], "adlf:o:p:hg", ["help", "gui"])
        except getopt.GetoptError:
            usage()
            sys.exit()
        managerargs = [sys.argv[0]]
        for o, a in opts:
            if o in ("-a", "-d", "-l"):
                managerargs.append(o)
            if o in ("-f", "-o", "-p"):
                managerargs.append(o, a)
            if o in ("-h", "--help"):
                usage()
                sys.exit()
            if o in ("-g", "--gui"):
                import Tkinter, tkFileDialog
                root = Tkinter.Tk()
                root.withdraw()
                sel = tkFileDialog.askopenfilenames(title="select W3C-SRGS grammar files")
                if isinstance(sel, unicode):
                    sel = root.tk.splitlist(sel)
                args.extend(sel)
        if len(args) <= 0:
            usage()
            sys.exit()
        self._grammars = args
        self._comp = {}
        self._manager = OpenRTM_aist.Manager.init(managerargs)
        self._manager.setModuleInitProc(self.moduleInit)
        self._manager.activateManager()

    def start(self):
        self._manager.runManager(False)

    def moduleInit(self, manager):
        profile = OpenRTM_aist.Properties(defaults_str = JuliusRTC_spec)
        manager.registerFactory(profile, JuliusRTC, OpenRTM_aist.Delete)
        for a in self._grammars:
            print "compiling grammar..."
            srgs = SRGS(a)
            print "done"
            self._comp[a] = manager.createComponent("JuliusRTC?exec_cxt.periodic.rate=1")
            self._comp[a].setgrammar(srgs)

def usage():
    print "usage: %s [-f rtc.conf] [--help] [--gui] [grammarfile]" % (os.path.basename(sys.argv[0]),)

def main():
    locale.setlocale(locale.LC_CTYPE, "")
    encoding = locale.getlocale()[1]
    if not encoding:
        encoding = "us-ascii"
    sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
    sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")
    manager = JuliusRTCManager()
    manager.start()

if __name__=='__main__':
    main()