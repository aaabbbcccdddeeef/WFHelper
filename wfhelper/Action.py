import re
import time
from os import path
from typing import Any, Dict, List
from asteval import Interpreter
from utils import Log, adbUtil
from .Global import GlobalState

aeval = Interpreter()


class ActionManager:
    def __init__(self, wfhelper):
        self.wfhelper = wfhelper

    def formatArg(self, arg):
        while isinstance(arg, str) and "$" in arg:
            argLeft = arg[: arg.rfind("$")]
            argRight = arg[arg.rfind("$") + 1:]
            if argLeft == "":
                tmp = GlobalState.getState(argRight)
                if tmp is None:
                    return None
                arg = tmp
            else:
                tmp = GlobalState.getState(argRight)
                if tmp is None:
                    return None
                arg = argLeft + GlobalState.getState(argRight)
        return arg

    def click(self, area: List[Any]):
        adbUtil.touchScreen(area)

    def sleep(self, args: List[Any]):
        time.sleep(args[0])

    def accessState(self, args: List[Any]):
        action, name, value = args

        name = self.formatArg(name)
        value = self.formatArg(value)
        if name is None:
            return

        if action == "set":
            GlobalState.setState(name, value)

        if action == "increase":
            if name == "无" or name is None:
                return
            if not GlobalState.has(name):
                GlobalState.setState(name, 0)
            value = int(value) + int(GlobalState.getState(name))
            GlobalState.setState(name, value)

    def changeTarget(self, args: List[Any]):
        name, targetName = args
        targets = self.wfhelper.config.targetList[name]

        return self.wfhelper.mainLoop(targets, targetName)

    def changeTargets(self, args: List[Any]):
        if len(args) == 2:
            name, mode = args
        else:
            name, mode = args[0], "once"

        targets = self.wfhelper.config.targetList[name]

        if mode == "loop":
            return GlobalState.setState("currentTargets", targets)

        if mode == "once":
            return self.changeTarget([name, None])

        return False

    def info(self, args: List[Any]):
        if len(args) == 0:
            Log.error("`info` action的参数不能为空")
            return
        tmp = []
        for t in args:
            t = self.formatArg(t)
            tmp.append(t)
        if len(tmp) == 1:
            Log.info(tmp[0])
        else:
            Log.info(tmp[0].format(*tmp[1:]))

    def getScreen(self, savePath: str):
        adbUtil.getScreen(savePath)

    def match(self, target: Dict[str, Any], args: List[Any]):
        exp, callbacks = args

        func = exp

        match = re.compile(r"\$[\u4E00-\u9FA5A-Za-z0-9_+\[\]·]+")
        items = re.findall(match, func)

        for item in items:
            func = func.replace(item, str(self.formatArg(item)))

        result = str(aeval(func))

        Log.debug("判断“{}”结果为: {}".format(exp, result))

        actions = None

        if result in callbacks:
            actions = callbacks[result]

        if actions is not None:
            self.doActions(target, actions)

    def doAction(self, target: Dict[str, Any], action: Dict[str, Any]):
        if action["name"] == "click":
            if (
                "args" not in action
                or len(action["args"]) == 0
                or action["args"][0] is None
            ):
                if "area" in target:
                    self.click(target["area"])
                else:
                    self.click(self.wfhelper.config.screenSize)
            else:
                self.click(action["args"][0])
        elif action["name"] == "sleep":
            self.sleep(action["args"])
        elif action["name"] == "state":
            self.accessState(action["args"])
        elif action["name"] == "changeTargets":
            self.changeTargets(action["args"])
        elif action["name"] == "changeTarget":
            self.changeTarget(action["args"])
        elif action["name"] == "info":
            self.info(action["args"])
        elif action["name"] == "exit":
            import sys

            sys.exit()
        elif action["name"] == "getScreen":
            if "args" not in action:
                savePath = path.join(
                    self.wfhelper.config.configDir,
                    "temp/{}.png".format(int(time.time())),
                )
                self.getScreen(savePath)
            else:
                self.getScreen(action["args"])
        elif action["name"] == "match":
            self.match(target, action["args"])
        else:
            Log.error(
                "action:'{}'不存在! 请检查'{}'的配置文件".format(action["name"], target["name"])
            )

    def doActions(self, target: Dict[str, Any], actions: List[Any] = None):
        if actions is None:
            actions = target["actions"]
        for action in actions:
            self.doAction(target, action)
