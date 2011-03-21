#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Base class for speech synthesis components

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import os
import sys
import time
import subprocess
import signal
import tempfile
import traceback
import platform
import codecs
import locale
import wave
import optparse
import OpenRTM_aist
import RTC
try:
    import gettext
    _ = gettext.translation(domain='openhrivoice', localedir=os.path.dirname(__file__)+'/../share/locale').ugettext
except:
    _ = lambda s: s

class VoiceSynthBase:
    def __init__(self):
        self._samplerate = 16000
        self._durationdata = ""
        self._fp = None
        self._wavefile = ""
        
    def gettempname(self):
        # get temp file name
        fn = tempfile.mkstemp()
        os.close(fn[0])
        return fn[1]

    def synth(self, data):
        pass
        
    def readdata(self, chunk):
        if self._fp is None:
            return None
        try:
            data = self._fp.readframes(chunk)
        except ValueError:
            self._fp.close()
            self._fp = None
            os.remove(self._wavfile)
            return None
        if data == '':
            self._fp.close()
            self._fp = None
            os.remove(self._wavfile)
            return None
        return data
    
    def terminate(self):
        pass

class DataListener(OpenRTM_aist.ConnectorDataListenerT):
    def __init__(self, name, obj):
        self._name = name
        self._obj = obj
    
    def __call__(self, info, cdrdata):
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self, info, cdrdata, RTC.TimedString(RTC.Time(0,0),""))
        self._obj.onData(self._name, data)

class VoiceSynthComponentBase(OpenRTM_aist.DataFlowComponentBase):
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._wrap = None

    def onInitialize(self):
        OpenRTM_aist.DataFlowComponentBase.onInitialize(self)
        self._logger = OpenRTM_aist.Manager.instance().getLogbuf(self._properties.getProperty("instance_name"))
        self._logger.RTC_INFO(self._properties.getProperty("type_name") + " version " + self._properties.getProperty("version"))
        self._logger.RTC_INFO("Copyright (C) 2010-2011 Yosuke Matsusaka")
        self._prevtime = time.clock()
        # create inport
        self._indata = RTC.TimedString(RTC.Time(0,0), "")
        self._inport = OpenRTM_aist.InPort("text", self._indata)
        self._inport.appendProperty('description', _('Text to be synthesized.').encode('UTF-8'))
        self._inport.addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                              DataListener("ON_BUFFER_WRITE", self))
        self.registerInPort(self._inport._name, self._inport)
        # create outport for wave data
        self._outdata = RTC.TimedOctetSeq(RTC.Time(0,0), None)
        self._outport = OpenRTM_aist.OutPort("result", self._outdata)
        self._outport.appendProperty('description', _('Synthesized audio data.').encode('UTF-8'))
        self.registerOutPort(self._outport._name, self._outport)
        # create outport for status
        self._statusdata = RTC.TimedString(RTC.Time(0,0), "")
        self._statusport = OpenRTM_aist.OutPort("status", self._statusdata)
        self._statusport.appendProperty('description', _('Status of audio output (one of "started", "finished").').encode('UTF-8'))
        self.registerOutPort(self._statusport._name, self._statusport)
        # create outport for duration data
        self._durdata = RTC.TimedString(RTC.Time(0,0), "")
        self._durport = OpenRTM_aist.OutPort("duration", self._durdata)
        self._durport.appendProperty('description', _('Time aliment information of each phonemes (to be used to lip-sync).').encode('UTF-8'))
        self.registerOutPort(self._durport._name, self._durport)
        return RTC.RTC_OK

    def onData(self, name, data):
        try:
            udata = data.data.decode("utf-8")
            self._logger.RTC_INFO(udata)
            if self._wrap is not None:
                self._wrap.synth(udata)
        except:
            self._logger.RTC_ERROR(traceback.format_exc())

    def onExecute(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onExecute(self, ec_id)
        try:
            # send stream
            now = time.clock()
            chunk = int(self._wrap._samplerate * (now - self._prevtime))
            data = None
            if chunk > 0:
                self._prevtime = now
                data = self._wrap.readdata(chunk)
            if data is not None:
                if self._statusdata.data != "started":
                    self._logger.RTC_INFO("streaming start")
                    self._statusdata.data = "started"
                    self._statusport.write(self._statusdata)
                    self._durdata.data = self._wrap._durationdata
                    self._durport.write(self._durdata)
                    data2 = self._wrap.readdata(int(self._wrap._samplerate * 1.0))
                    if data2 is not None:
                        data += data2
                self._outdata.data = data
                self._outport.write(self._outdata)
            else:
                if self._statusdata.data != "finished":
                    self._logger.RTC_INFO("streaming finished")
                    self._statusdata.data = "finished"
                    self._statusport.write(self._statusdata)
        except:
            self._logger.RTC_ERROR(traceback.format_exc())
        return RTC.RTC_OK

    def onFinalize(self):
        OpenRTM_aist.DataFlowComponentBase.onFinalize(self)
        self._wrap.terminate()
        return RTC.RTC_OK
