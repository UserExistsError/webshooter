from collections.abc import Collection
import xml.etree.ElementTree as ET

def from_xml(xml_file: str, http_ports: Collection[int], https_ports: Collection[int]) -> set[str]:
    scan = ET.parse(xml_file).getroot()
    if not scan.tag == 'NessusClientData_v2':
        raise ValueError('xml file is not NessusClientData_v2 format')
    urls = set()
    for report_host in scan.iterfind('./Report/ReportHost'):
        host: str = report_host.get('name')
        for report_item in report_host.iterfind('./ReportItem[@protocol="tcp"]'):
            port: int = int(report_item.get('port'))
            if port in http_ports:
                if port == 80:
                    urls.add('http://{}/'.format(host))
                else:
                    urls.add('http://{}:{}/'.format(host, port))
            if port in https_ports:
                if port == 443:
                    urls.add('https://{}/'.format(host))
                else:
                    urls.add('https://{}:{}/'.format(host, port))
    return urls
