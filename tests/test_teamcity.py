import json
import unittest
from unittest.mock import patch

from app import app

request_data = {
    "alias": "model2041-lv",
    "ID": "7f2a6b70-72af-4264-bb9d-d6b73c2eabd5",
    "messageName": "validation_result",
    "processInstanceId": "c281286d-7efd-498a-8d38-1c4e7951c4ca",
    "df_pth_val": "first_validation_data.pdf",
    "df_pth_dev": "first_validation_data_developing.pdf",
    "config": "first_validation_config.pdf",
    "scale": '[{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":59,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2",'
             '"SCALE_RANK_MIN":1,"SCALE_RANK_AVG":1,"SCALE_RANK_MAX":2}, {"ROOT_RISK_SCALE_ID":238,'
             '"SYS_SCALE_RANK_ID":61,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2","SCALE_RANK_MIN":3,'
             '"SCALE_RANK_AVG":5,"SCALE_RANK_MAX":7},{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":60,'
             '"SCALE_RANK_ID":"2","SCALE_RANK_CAT":"MD3","SCALE_RANK_MIN":2,"SCALE_RANK_AVG":2,'
             '"SCALE_RANK_MAX":3}]',
    "path_out": "first_auto_validation_report.xlsx",
}

post_content = """<?xml version='1.0' encoding='utf-8'?>
    <build>
        <buildType id = "SumValidationCi_Validation"/>
        <properties>
            <property name = "env.MODELNAME" value = "model2041"/>
            <property name = "env.MODELVERSION" value = "lv"/>
            <property name = "env.MODELID" value = "7f2a6b70-72af-4264-bb9d-d6b73c2eabd5"/>
            <property name = "env.messageName" value = "validation_result"/>
            <property name = "env.processInstanceId" value = "c281286d-7efd-498a-8d38-1c4e7951c4ca"/>
            <property name = "env.DFPTHVAL" value = "first_validation_data.pdf"/>
            <property name = "env.DFPTHDEV" value = "first_validation_data_developing.pdf"/>
            <property name = "env.PATHOUT" value = "first_auto_validation_report.xlsx"/>
            <property name = "env.CONFIG" value = "first_validation_config.pdf"/>
            <property name = "env.SCALE" value = '[{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":59,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2","SCALE_RANK_MIN":1,"SCALE_RANK_AVG":1,"SCALE_RANK_MAX":2},{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":61,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2","SCALE_RANK_MIN":3,"SCALE_RANK_AVG":5,"SCALE_RANK_MAX":7},{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":60,"SCALE_RANK_ID":"2","SCALE_RANK_CAT":"MD3","SCALE_RANK_MIN":2,"SCALE_RANK_AVG":2,"SCALE_RANK_MAX":3}]'/>
        </properties>
    </build>"""

result_message = {'id': 'SumValidationCi_Validation', 'env.MODELNAME': 'model2041',
                  'env.MODELVERSION': 'lv', 'env.MODELID': '7f2a6b70-72af-4264-bb9d-d6b73c2eabd5',
                  'env.messageName': 'validation_result',
                  'env.processInstanceId': 'c281286d-7efd-498a-8d38-1c4e7951c4ca',
                  'env.DFPTHVAL': 'first_validation_data.pdf',
                  'env.DFPTHDEV': 'first_validation_data_developing.pdf',
                  'env.PATHOUT': 'first_auto_validation_report.xlsx',
                  'env.CONFIG': 'first_validation_config.pdf',
                  'env.SCALE': '[{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":59,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2","SCALE_RANK_MIN":1,"SCALE_RANK_AVG":1,"SCALE_RANK_MAX":2},{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":61,"SCALE_RANK_ID":"1","SCALE_RANK_CAT":"MD2","SCALE_RANK_MIN":3,"SCALE_RANK_AVG":5,"SCALE_RANK_MAX":7},{"ROOT_RISK_SCALE_ID":238,"SYS_SCALE_RANK_ID":60,"SCALE_RANK_ID":"2","SCALE_RANK_CAT":"MD3","SCALE_RANK_MIN":2,"SCALE_RANK_AVG":2,"SCALE_RANK_MAX":3}]'}


class TestTeamcity(unittest.TestCase):

    @patch('app.teamcity.requests.post')
    def test_start_validation(self, post):
        with app.test_client() as client:
            post.return_value.text = "HELLO"
            post.return_value.content = post_content
            post.return_value.status_code = 200
            response = client.post('/teamcity/validation/start', data=json.dumps(request_data),
                                   content_type='application/json')
            result = json.loads(response.data)
            self.assertEquals(response.status_code, 200)
            self.assertEquals(result['status'], 'ok')
            self.assertEquals(result['message'], result_message)
