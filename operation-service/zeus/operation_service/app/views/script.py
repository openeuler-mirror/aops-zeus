from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse

from zeus.operation_service.app.serialize.script import ModifyScriptSchema, GetScriptSchema, AddScriptSchema, ScriptSchema
from zeus.operation_service.app.proxy.script import ScriptProxy
from flask import request

class ScriptManageAPI(BaseResponse):
    @BaseResponse.handle(schema=GetScriptSchema, proxy=ScriptProxy)
    def get(self, callback: ScriptProxy, **params):
        """
        Get scripts

        Args:
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_scripts(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=AddScriptSchema, proxy=ScriptProxy)
    def post(self, callback: ScriptProxy, **params):
        status_code, script_id = callback.add_script(params)
        return self.response(code=status_code, data=script_id)

    
    @BaseResponse.handle(proxy=ScriptProxy)
    def delete(self, callback: ScriptProxy, **params):
        status_code, result = callback.batch_delete_script(params['script_ids'])
        return self.response(code=status_code, data=result)
    

class ScriptInfoManageAPI(BaseResponse):

    @BaseResponse.handle(proxy=ScriptProxy)
    def get(self, callback: ScriptProxy, script_id, **params):
        status_code, script, operate_id = callback.get_script_info(script_id)
        if script:
            script =  ScriptSchema().dump(script)
            script['operate_id'] = operate_id
        return self.response(code=status_code, data=script)
    
    @BaseResponse.handle(schema=ModifyScriptSchema, proxy=ScriptProxy)
    def put(self, callback: ScriptProxy, script_id, **params):
        status_code, script = callback.modify_script_info(script_id, params)
        if script:
            script =  ScriptSchema().dump(script)
        return self.response(code=status_code, data=script)
    
    @BaseResponse.handle(proxy=ScriptProxy)
    def post(self, callback: ScriptProxy, script_id, **params):
        status_code = callback.upload_file(script_id, params)
        return self.response(code=status_code)


class SupportOSInfoManageAPI(BaseResponse):
    @BaseResponse.handle(proxy=ScriptProxy)
    def get(self, callback: ScriptProxy, **params):
        status_code, info = callback.get_support_os_info()
        return self.response(code=status_code, data=info)
