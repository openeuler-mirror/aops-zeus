from vulcanus.log.log import LOGGER
from vulcanus.restful.resp import state
from vulcanus.restful.response import BaseResponse

from zeus.operation_service.app.serialize.command import ModifyCommandSchema, GetCommandSchema, AddCommandSchema, CommandSchema
from zeus.operation_service.app.proxy.command import CommandProxy

class CommandManageAPI(BaseResponse):
    @BaseResponse.handle(schema=GetCommandSchema, proxy=CommandProxy)
    def get(self, callback: CommandProxy, **params):
        """
        Get commands

        Args:
            sort (str): sort according to specified field
            direction (str): sort direction
            page (int): current page
            per_page (int): count per page

        Returns:
            dict: response body
        """
        status_code, result = callback.get_commands(params)
        return self.response(code=status_code, data=result)

    @BaseResponse.handle(schema=AddCommandSchema, proxy=CommandProxy)
    def post(self, callback: CommandProxy, **params):
        status_code = callback.add_command(params)
        return self.response(code=status_code)

    
    @BaseResponse.handle(proxy=CommandProxy)
    def delete(self, callback: CommandProxy, **params):
        status_code, result = callback.batch_delete_command(params['command_ids'])
        return self.response(code=status_code, data=result)
    

class CommandInfoManageAPI(BaseResponse):

    @BaseResponse.handle(proxy=CommandProxy)
    def get(self, callback: CommandProxy, command_id, **params):
        status_code, command = callback.get_command_info(command_id)
        if command:
            command =  CommandSchema().dump(command)
        return self.response(code=status_code, data=command)
    
    @BaseResponse.handle(schema=ModifyCommandSchema, proxy=CommandProxy)
    def put(self, callback: CommandProxy, command_id, **params):
        status_code, command = callback.modify_command_info(command_id, params)
        if command:
            command =  CommandSchema().dump(command)
        return self.response(code=status_code, data=command)
