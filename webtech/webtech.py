from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
import re

class webtech(BHunters):
    """
    Detect web technology developed by Bormaa
    """

    identity = "B-Hunters-web-technology"
    version = __version__
    persistent = True
    filters = [
        {
            "type": "url", "stage": "new"
        },
        {
            "type": "path", "stage": "new"
        }
        ,
        {
            "type": "subdomain", "stage": "new"
        }
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
    def techsfind(self,url):
        try:
            filename=self.generate_random_filename()
            output=subprocess.run(["wappy","-u", url,"-wf",filename], capture_output=True, text=True)
            data=""
            if os.path.exists(filename) and os.path.getsize(filename) > 0:  # Check if file exists and is not empty
                with open(filename, 'r') as file:
                    try:
                        data = file.read()
                    except Exception as e:
                        print("Error:",e)
                        result=""
            else:
                result=""
            if data!="":
                matches = re.search(r'TECHNOLOGIES\[(.*?)\]:', data, re.DOTALL)
                if matches:
                    end_index = matches.end()
                    lines_after_match = data[end_index:].split('\n')
                    # print(lines_after_match)
                    techs=[]
                    for i in lines_after_match:
                        if i != "":
                            splitwithcollon=i.split(" :")
                            version=splitwithcollon[1].split("[version:")
                            servicetype=splitwithcollon[0]
                            service=version[0]
                            serviceversion=version[1].replace("]", "")
                            if "tag" not in servicetype.lower() and "font" not in servicetype.lower()  and "seo" not in servicetype.lower() and "database" not in servicetype.lower() and "video player" not in servicetype.lower() and "cdn" not in servicetype.lower():

                                techs.append([servicetype.strip(),service.strip(),serviceversion.strip()])
                    result=techs
                else:
                    result=""
            
        except Exception as e:
            print("error ",e)
            result=""
        return result
                
    def scan(self,url):        
        result=self.techsfind(url)
        if result !="":
            return result
        return ""
        
    def process(self, task: Task) -> None:
        if task.payload["source"] == "producer":
            url = task.payload_persistent["domain"]
        else:
            url = task.payload["data"]
        newurl=self.add_https_if_missing(url)
        collection=self.db["domains"]
        self.log.info("Starting processing new url")
        self.log.warning(url)
        result=self.scan(url)
        subdomain=task.payload["subdomain"]
        subdomain = re.sub(r'^https?://', '', subdomain)
        subdomain = subdomain.rstrip('/')

        if result !="":
            for i in result:
                if "wordpress" in i[1].lower():
                    wordpress_task = Task(
                    {"type": "url", "stage": "wordpress"},
                    payload={"data": url,
                             "subdomain":subdomain
                    }
                )
                    self.send_task(wordpress_task)
            domain_document = collection.find_one({"Domain": subdomain})
            if domain_document:
                if "Technology" in domain_document and "wappy" in domain_document["Technology"]:
                    collection.update_one({"Domain": subdomain}, {"$push": {"Technology.wappy": {newurl: result}}})
                else:
                    collection.update_one({"Domain": subdomain}, {"$set": {"Technology.wappy": [{newurl: result}]}})
            else:
                collection.update_one({"Domain": subdomain}, {"$set": {"Technology": {"wappy": [{newurl: result}]}}})
