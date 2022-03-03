import uuid
import redis, json
import requests
import logging
from dataclasses import asdict
from typing import List
from auth_helper import dss_auth_helper
from rid_operations.tasks import submit_dss_subscription
from .scd_data_definitions import ImplicitSubscriptionParameters, Volume4D, OperationalIntentReference,DSSOperationalIntentCreateResponse, OperationalIntentReferenceDSSResponse, Time
from os import environ as env
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
 
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

logger = logging.getLogger('django')

class SCDOperations():
    def __init__(self):
        self.dss_base_url = env.get('DSS_BASE_URL')        
        self.r = redis.Redis(host=env.get('REDIS_HOST',"redis"), port =env.get('REDIS_PORT',6379))  
    
    def create_operational_intent_reference(self, state:str, priority:str, volumes:List[Volume4D], off_nominal_volumes:List[Volume4D]):        
        my_authorization_helper = dss_auth_helper.AuthorityCredentialsGetter()
        audience = env.get("DSS_SELF_AUDIENCE", 0)        
        try: 
            assert audience
        except AssertionError as ae:
            logger.error("Error in getting Authority Access Token DSS_SELF_AUDIENCE is not set in the environment")

        try:
            auth_token = my_authorization_helper.get_cached_credentials(audience= audience, token_type='scd')
        except Exception as e:
            logger.error("Error in getting Authority Access Token %s " % e)            
        else:
            error = auth_token.get("error")            
        
        # A token from authority was received, we can now submit the operational intent
        new_entity_id = str(uuid.uuid4())
        dss_subscription_url = self.dss_base_url + 'dss/v1/operational_intent_references/' + new_entity_id
        headers = {"Content-Type": "application/json", 'Authorization': 'Bearer ' + auth_token['access_token']}
        management_key = str(uuid.uuid4())        
        blender_base_url = env.get("BLENDER_FQDN", 0)
        implicit_subscription_parameters = ImplicitSubscriptionParameters(uss_base_url=blender_base_url)
        operational_intent_reference = OperationalIntentReference(extents = [asdict(volumes[0])], key =[management_key], state = state, uss_base_url = blender_base_url, new_subscription = implicit_subscription_parameters)

        p = json.loads(json.dumps(asdict(operational_intent_reference)))

        try:
            dss_r = requests.put(dss_subscription_url, json =p , headers=headers)
        except Exception as re:
            logger.error("Error in putting operational intent in the DSS %s " % re)
            
        d_r ={}
        
        try: 
            assert dss_r.status_code == 201            
        except AssertionError as ae:              
            logger.error("Error submitting operational intent to the DSS %s" % dss_r.text)            
        else: 	        
            dss_response = dss_r.json()
            subscribers = dss_response['subscribers']
            o_i_r = dss_response['operational_intent_reference']
            time_start = Time(format=o_i_r['time_start']['format'], value=o_i_r['time_start']['value'])
            time_end = Time(format=o_i_r['time_end']['format'], value=o_i_r['time_end']['value'])
            operational_intent_r = OperationalIntentReferenceDSSResponse(id=o_i_r['id'], manager=o_i_r['manager'],uss_availability=o_i_r['uss_availability'], version=o_i_r['version'], state = o_i_r['state'], ovn= o_i_r['ovn'], time_start=time_start, time_end=time_end, uss_base_url=o_i_r['uss_base_url'], subscription_id=o_i_r['subscription_id'])

            dss_creation_response = DSSOperationalIntentCreateResponse(operational_intent_reference=operational_intent_r, subscribers=subscribers)
            logger.success("Successfully created operational intent in the DSS %s" % dss_r.text)
            d_r = asdict(dss_creation_response)
        return d_r
            
        