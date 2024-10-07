# Copyright (c) NVIDIA CORPORATION
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import re
import json
import logging
import sys
import atexit
import io
from enum import Enum
from datetime import datetime

from ocptv.output import  Writer


class JsonFormatter(logging.Formatter):
    def format(self, record):
        """
        :Description:                       Format method for formatting data into json output

        :param JSON Dict record:		    Dict object for Log JSON Data

        :returns:                           JSON object with indent 4
        :rtype                              JSON Dict
        """
        msg = json.loads(getattr(record, "msg", None))
        f_msg = json.dumps(msg, indent=4) 
        return f_msg + ","


class BuiltInLogSanitizers(Enum):
    '''
    Supported Built-In log sanitizer regex
    '''
    IPV4 = "ipv4_address"
    IPV6 = "ipv6_address"
    CURL = "curl_command"
    PASSWORD = "passwords"


class LogSanitizer(logging.Formatter):
    '''
    Class to handle log sanitization
    '''
    builtin_regex = {
        BuiltInLogSanitizers.IPV6: r'^([0-9a-fA-F]{1,4}:){6}((:[0-9a-fA-F]{1,4}){1,2}|:)',
        BuiltInLogSanitizers.IPV4: r'((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])',
        BuiltInLogSanitizers.CURL: r'-u\s*(\"([^\"]+:[^\"]+)\")',
        BuiltInLogSanitizers.PASSWORD: r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$%!&?&.])[A-Za-z\d@.$%!*&?]{8,}",
    }

    def __init__(self, fmt=None, datefmt=None, style='%', string_list=None,
                replacement_string='XXXX', words_to_skip=[],
                additional_regex=[]):
        """
        Sanitizer constructor. Provide the list of strings to filter out from the logs

        :param fmt                  : Format string style. Doesn't affect sanitize() output.
                                      Refer to logging.Formatter for more details
        :type fmt                   : str
        :param datefmt              : Format style for date/time. Doesn't affect sanitize() output.
                                      Refer to logging.Formatter for more details
        :type datefmt               : str
        :param style                : Determines how the format string will be merged.
                                      Refer to logging.Formatter for more details
        :type style                 : str
        :param string_list          : List of strings to filter out
        :type string_list           : list of str
        :param replacement_string   : String to replace target strings. Default is XXXX
        :type replacement_string    : str
        :param additional_regex     : List of in-built log collectors to be used
        :type additional_regex      : list of BuiltInLogSanitizers
        """
        default_regex = [BuiltInLogSanitizers.IPV4, BuiltInLogSanitizers.IPV6]
        if additional_regex:
            additional_regex.extend(default_regex)
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.compiled_string = None
        
        if not isinstance(string_list, list):
            string_list = []
        string_list = list(
            map(lambda x: r'(?<!\w)' + re.escape(x) + r'(?!\w)', string_list))
        for regex in additional_regex:
            string_list.append(self.builtin_regex[regex])
        if words_to_skip:
            string_list.extend(words_to_skip)
        if len(string_list) == 0:
            return
        self.compiled_string = re.compile('|'.join(string_list), flags=re.M)
        self.replacement = replacement_string

    def sanitize(self, string):
        """
        Sanitizes a given string based on initialized strings and in-built sanitizers

        :param string       : String to be sanitized
        :type string        : str

        :return             : string
        :rtype              : str
        """
        return (re.sub(self.compiled_string, self.replacement, string)
                if self.compiled_string else string)

    def format(self, record):
        return self.sanitize(record)


class LoggingWriter(Writer):
    """
    Helper class registers python logger with OCP logger to be used for file output etc

    :param Writer: OCP Writer super class
    :type Writer:
    """

    def __init__(self, output_dir, console_log, testrun_name,extension_name,  debug, desanitize_log=False,
                 words_to_skip=[]):
        """
        Initialize file logging parameters

        :param output_dir: location of log file
        :type output_dir: str
        :param console_log: true if desired to print to console as well as log
        :type console_log: bool
        :param testrun_name: name for current testrun
        :type testrun_name: str
        :param debug: if true, log LogSeverity.DEBUG messages
        :type debug: 
        :desanitize_log: if true, will mask private details in log output
        :type bool
        """
        dt = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        file_name_tmp = "/{}_{}.{}".format(testrun_name, dt, extension_name)
        # Create a logger
        self.logger = logging.getLogger(file_name_tmp)
        self.debug = debug

        # Set the level for this logger. This means that unless specified otherwise, all messages
        # with level INFO and above will be logged.
        # If you want to log all messages you can use logging.DEBUG
        self.logger.setLevel(logging.DEBUG)

        # Create formatters and add them to the handlers
        # formatter = logging.Formatter("%(message)s")

        # Create a file handler that logs messages to a file
        self.__log_file = output_dir + file_name_tmp
        self.file_handler = logging.FileHandler(output_dir + file_name_tmp)
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(FileJsonFormatter())
        self.logger.addHandler(self.file_handler)
        self.desanitize_log = desanitize_log
        self.sanitizer = LogSanitizer(words_to_skip=words_to_skip)

        if console_log:
            # Create a console handler that logs messages to the console
            self.console_handler = logging.StreamHandler()
            self.console_handler.setLevel(logging.DEBUG)
            self.console_handler.setFormatter(StreamJsonFormatter())
            self.logger.addHandler(self.console_handler)

    def write(self, buffer: str):
        """
        Called from the OCP framework for logging messages.  Use debug switch to filter
        LogSeverity.DEBUG messages.

        :param buffer: _description_
        :type buffer: str
        """
        if not self.debug:
            if '"severity": "debug"' in buffer.lower():
                return
        if self.desanitize_log:
            buffer = self.sanitizer.format(buffer)
    
        if '"severity": "info"' in buffer.lower():
            self.logger.info(buffer)
        elif '"severity": "error"' in buffer.lower():
            self.logger.error(buffer)
        elif '"severity": "warning"' in buffer.lower():
            self.logger.warning(buffer)
        elif '"severity": "fatal"' in buffer.lower():
            self.logger.error(buffer)
        elif '"severity": "debug"' in buffer.lower():
            self.logger.debug(buffer)
        else:
            self.logger.info(buffer)
        
    def log(self, msg: str):
        """
        Called from the OCP framework for logging messages. This method is a wrapper
        of the "write" method to add timestamp to a message.

        :param msg: Message to be logged
        :type msg: str
        """
        json_msg = {
            "TimeStamp": datetime.now().strftime("%m-%d-%YT%H:%M:%S"),
            "Message": msg}
        self.write(json.dumps(json_msg))

    @property
    def log_file(self):
        return self.__log_file


class FileJsonFormatter(logging.Formatter):
    def format(self, record):
        """
        :Description:                       Format method for formatting data into json output

        :param JSON Dict record:		    Dict object for Log JSON Data

        :returns:                           JSON object with indent 4
        :rtype                              JSON Dict
        """
        msg = json.loads(getattr(record, "msg", None))
        log_msg = super().format(record)
        log_msg = json.dumps(msg, indent=4) 
        if record.levelno == logging.ERROR:
            return f"{log_msg},"
        elif record.levelno == logging.WARNING:
            return f"{log_msg},"
        elif record.levelno == logging.INFO:
            return f"{log_msg},"
        elif record.levelno == logging.DEBUG:
            return f"{log_msg},"



class StreamJsonFormatter(logging.Formatter):
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    def format(self, record):
        """
        :Description:                       Format method for formatting data into json output

        :param JSON Dict record:		    Dict object for Log JSON Data

        :returns:                           JSON object with indent 4
        :rtype                              JSON Dict
        """
        msg = json.loads(getattr(record, "msg", None))
        log_msg = super().format(record)
        log_msg = json.dumps(msg, indent=4) 
        if record.levelno == logging.ERROR:
            return f"{StreamJsonFormatter.RED}{log_msg}{StreamJsonFormatter.RESET},"
        elif record.levelno == logging.WARNING:
            return f"{StreamJsonFormatter.YELLOW}{log_msg}{StreamJsonFormatter.RESET},"
        elif record.levelno == logging.INFO:
            return f"{StreamJsonFormatter.GREEN}{log_msg}{StreamJsonFormatter.RESET},"
        elif record.levelno == logging.DEBUG:
            return f"{StreamJsonFormatter.BLUE}{log_msg}{StreamJsonFormatter.RESET},"




class TeeStream(io.IOBase):
    def __init__(self, *streams):
        self.streams = streams
 
    def write(self, message):
        if not self.check_progress_message(message):
            for stream in self.streams:
                stream.write(message)
                stream.flush()
        else:
            self.streams[0].write(message)
            self.streams[0].flush()
 
    def flush(self):
        for stream in self.streams:
            stream.flush()
            
    def check_progress_message(self, message):
        pattern = r"[|\\\/\-#]+\s*\|\s*\d+\s*Elapsed\sTime:\s*\d+:\d+:\d+"
        matches = re.findall(pattern, message)
        return True if matches else False
 
class RedirectOutput:
    def __init__(self, logfile=""):
        self.logfile = logfile
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_file = open(logfile, 'a+', buffering=1)
        self.stdout_tee = TeeStream(self.original_stdout, self.log_file)
        self.stderr_tee = TeeStream(self.original_stderr, self.log_file)
        atexit.register(self.restore)
    
    def start(self):
        sys.stdout = self.stdout_tee
        sys.stderr = self.stderr_tee

    def temporary_stop(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
    def restore(self):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.log_file.close()