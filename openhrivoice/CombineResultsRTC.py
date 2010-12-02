#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''CombineResultsRTC (combine results from speech recognizers)

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import sys
import codecs
import time
import signal
import re
import traceback
import socket
import threading
import OpenRTM_aist
import RTC
from xml.dom import minidom

CombineResultsRTC_spec = ["implementation_id", "CombineResultsRTC",
                          "type_name",         "CombineResultsRTC",
                          "description",       "Combine Results from Speech Recognizers",
                          "version",           "1.0.0",
                          "vendor",            "Yosuke Matsusaka, AIST",
                          "category",          "Speech",
                          "activity_type",     "DataFlowComponent",
                          "max_instance",      "1",
                          "language",          "Python",
                          "lang_type",         "script",
                          ""]

class DataListener(OpenRTM_aist.ConnectorDataListenerT):
    def __init__(self, name, obj):
        self._name = name
        self._obj = obj
    
    def __call__(self, info, cdrdata):
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self, info, cdrdata, RTC.TimedString(RTC.Time(0,0),""))
        self._obj.onData(self._name, data)

class CombineResultsRTC(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._data = {}
        self._port = {}
        self._statusports = ('status1', 'status2')
        self._resultports = ('result1', 'result2')
        self._results = {}
        self._maxprob = {}
        self._listening = 0
        self.createInPort('status1', RTC.TimedString)
        self.createInPort('result1', RTC.TimedString)
        self.createInPort('status2', RTC.TimedString)
        self.createInPort('result2', RTC.TimedString)
        self.createOutPort('statusout', RTC.TimedString)
        self.createOutPort('resultout', RTC.TimedString)
    
    def createInPort(self, name, type=RTC.TimedString):
        print "create inport: " + name
        self._data[name] = type(RTC.Time(0,0), None)
        self._port[name] = OpenRTM_aist.InPort(name, self._data[name])
        self.registerInPort(name, self._port[name])
        self._port[name].addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                                  DataListener(name, self))
        self._results[name] = ''
        self._maxprob[name] = -float("inf")

    def createOutPort(self, name, type=RTC.TimedString):
        print "create outport: " + name
        self._data[name] = type(RTC.Time(0,0), None)
        self._port[name] = OpenRTM_aist.OutPort(name, self._data[name], OpenRTM_aist.RingBuffer(8))
        self.registerOutPort(name, self._port[name])

    def onData(self, name, data):
        try:
            self.processResult(name, data.data)
        except:
            print traceback.format_exc()

    def onExecute(self, ec_id):
        time.sleep(1)
        return RTC.RTC_OK

    def processResult(self, host, s):
        #print "got input %s (%s)" % (s, host)
        self._results[host] = s
        if host[:-1] == 'result':
            hearing = False
            for p in self._statusports:
                if self._results[p] == 'STARTREC':
                    hearing = True
            if hearing == False:
                results = list()
                for p in self._resultports:
                    if self._results[p] != '':
                        doc = minidom.parseString(self._results[p])
                        for s in doc.getElementsByTagName('data'):
                            prob = float(s.getAttribute('likelihood'))
                            if prob > self._maxprob[p]:
                                self._maxprob[p] = prob
                            results.append((prob/self._maxprob[p], s))
                results.sort(key = lambda x:x[0])
                doc = minidom.Document()
                listentext = doc.createElement("listenText")
                doc.appendChild(listentext)
                rank = 1
                for r in results:
                    listentext.appendChild(r[1])
                    r[1].setAttribute("rank", str(rank))
                    rank += 1
                retstr = doc.toxml(encoding="utf-8")
                print retstr
                self._data['resultout'].data = retstr
                self._port['resultout'].write(self._data['resultout'])

class CombineResultsRTCManager:
    def __init__(self):
        self.comp = None
        self.manager = OpenRTM_aist.Manager.init([])
        self.manager.setModuleInitProc(self.moduleInit)
        self.manager.activateManager()

    def start(self):
        self.manager.runManager(False)

    def moduleInit(self, manager):
        profile=OpenRTM_aist.Properties(defaults_str=CombineResultsRTC_spec)
        manager.registerFactory(profile, CombineResults, OpenRTM_aist.Delete)
        self.comp = manager.createComponent("CombineResultsRTC?exec_cxt.periodic.rate=1")

def main():
    mainloop = True
    manager = CombineResultsRTCManager()
    manager.start()

if __name__=='__main__':
    main()
