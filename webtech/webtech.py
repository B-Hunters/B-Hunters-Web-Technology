from .__version__ import __version__
import subprocess
import json
import os
from urllib.parse import urlparse
from b_hunters.bhunter import BHunters
from karton.core import Task
import re
from bson.objectid import ObjectId

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
        """Fingerprint the technologies of a URL.

        The tool is the Go rewrite of wappalyzer-cli, which offers a JSON
        output.  The result keeps the shape the report document expects: a
        list of ``[category, name, version]`` entries.
        """
        try:
            output=subprocess.run(
                ["wappy","-u", url,"--format","json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if output.returncode != 0 or not output.stdout:
                self.log.error(f"wappy failed for {url}: {output.stderr[:200]}")
                return ""
            try:
                document = json.loads(output.stdout)
            except ValueError as exc:
                self.log.error(f"wappy returned invalid JSON for {url}: {exc}")
                return ""

            techs=[]
            for result in document.get("results", []) or []:
                for technology in result.get("technologies", []) or []:
                    name = str(technology.get("name", "")).strip()
                    if not name:
                        continue
                    categories = technology.get("categories", []) or []
                    category = str(categories[0]) if categories else "unknown"
                    version = str(technology.get("version", "") or "")
                    techs.append([category, name, version])
            if not techs:
                return ""
            return techs
        except Exception as e:
            self.log.error(f"wappy failed for {url}: {e}")
            return ""

    def scan(self,url):        
        result=self.techsfind(url)
        if result !="":
            return result
        return ""
        
    def process(self, task: Task) -> None:
        # The host being processed is the per-task subdomain, exactly as
        # every other worker uses.  The persistent root domain is only the
        # starting point of a scan.
        subdomain=task.payload["subdomain"]
        subdomain = re.sub(r'^https?://', '', subdomain)
        subdomain = subdomain.rstrip('/')
        if task.payload["source"] == "producer":
            url = task.payload_persistent["domain"]
        else:
            url = task.payload["data"]
        newurl=self.add_https_if_missing(url)
        self.scanid=task.payload_persistent["scan_id"]
        report_id=task.payload_persistent["report_id"]
        self.log.info("Starting processing new url")
        self.update_task_status(subdomain,"Started")
        try:
            result=self.scan(url)
        except Exception as e:
            self.log.error(e)
            self.update_task_status(subdomain,"Failed")
            raise
        self.log.warning(url)
        self.waitformongo()
        collection=self.db["reports"]

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
            domain_document = collection.find_one({"_id": ObjectId(report_id)})
            if domain_document:
                if "Technology" in domain_document and "wappy" in domain_document["Technology"]:
                    collection.update_one({"_id": ObjectId(report_id)}, {"$push": {"Technology.wappy": {newurl: result}}})
                else:
                    collection.update_one({"_id": ObjectId(report_id)}, {"$set": {"Technology.wappy": [{newurl: result}]}})
            else:
                collection.update_one({"_id": ObjectId(report_id)}, {"$set": {"Technology": {"wappy": [{newurl: result}]}}})

        self.update_task_status(subdomain,"Finished")