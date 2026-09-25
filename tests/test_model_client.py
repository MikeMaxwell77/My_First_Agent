"""Provider adapter contract tested without network access."""
from types import SimpleNamespace
from model_client import OpenAIModelClient


class FakeResponses:
    def __init__(self):
        self.requests = []
    def create(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            return SimpleNamespace(id='response-1', output=[SimpleNamespace(type='function_call',
                name='get_customer', arguments='{"customer_id":"123"}', call_id='call-1')])
        return SimpleNamespace(id='response-2', output=[], output_text=
            '{"final_answer":"Appears eligible","determination":"ELIGIBLE","reason":"Evidence"}')


def test_adapter_preserves_call_ids_and_conversation():
    responses = FakeResponses()
    client = OpenAIModelClient(client=SimpleNamespace(responses=responses))
    first = client.generate([{'input':'test'}], [])
    assert first.calls[0].call_id == 'call-1'
    final = client.generate([{'input':[]}], [])
    assert final.determination == 'ELIGIBLE'
    assert responses.requests[1]['previous_response_id'] == 'response-1'
    assert responses.requests[1]['instructions'] == responses.requests[0]['instructions']


def test_unstructured_answer_is_unknown():
    class Responses:
        def create(self, **kwargs):
            return SimpleNamespace(id='id',output=[],output_text='Unstructured response')
    client = OpenAIModelClient(client=SimpleNamespace(responses=Responses()))
    result = client.generate([{'input':'test'}], [])
    assert result.determination == 'UNKNOWN'
    assert 'Unstructured' in result.reason
