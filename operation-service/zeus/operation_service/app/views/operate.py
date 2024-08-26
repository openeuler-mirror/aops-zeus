from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse

from zeus.operation_service.app.serialize.operate import ModifyOperateSchema, GetOperateSchema, AddOperateSchema, OperateSchema
from zeus.operation_service.app.proxy.operate import OperateProxy

class OperateManageAPI(BaseResponse):
    @BaseResponse.handle(schema=GetOperateSchema, proxy=OperateProxy)
    def get(self, callback: OperateProxy, **params):
        """
        Get operates

        Args:
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_operates(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=AddOperateSchema, proxy=OperateProxy)
    def post(self, callback: OperateProxy, **params):
        status_code = callback.add_operate(params)
        return self.response(code=status_code)

    
    @BaseResponse.handle(proxy=OperateProxy)
    def delete(self, callback: OperateProxy, **params):
        status_code, result = callback.batch_delete_operate(params['operate_ids'])
        return self.response(code=status_code, data=result)
    

class OperateInfoManageAPI(BaseResponse):

    @BaseResponse.handle(proxy=OperateProxy)
    def get(self, callback: OperateProxy, operate_id, **params):
        status_code, operate = callback.get_operate_info(operate_id)
        if operate:
            operate =  OperateSchema().dump(operate)
        return self.response(code=status_code, data=operate)
    
    @BaseResponse.handle(schema=ModifyOperateSchema, proxy=OperateProxy)
    def put(self, callback: OperateProxy, operate_id, **params):
        status_code, operate = callback.modify_operate_info(operate_id, params)
        if operate:
            operate =  OperateSchema().dump(operate)
        return self.response(code=status_code, data=operate)
