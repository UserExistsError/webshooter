from collections.abc import Collection
import xml.etree.ElementTree as ET

def from_xml(xml_file: str, http_ports: Collection[int], https_ports: Collection[int]) -> list[str]:
    scan = ET.parse(xml_file).getroot()
    if not scan.tag == 'nmaprun':
        raise ValueError('xml file is not nmap format')
    urls = set()
    for host in scan.findall('./host'):
        open_ports = [int(p.get('portid')) for p in host.findall('./ports/port') if p.find('state').get('state') == 'open']
        for p in open_ports:
            addr = host.findall('./address')[0].get('addr')
            # use hostname if present. reverse lookups are ignored.
            names = [h.get('name') for h in host.findall('./hostnames/hostname') if h.get('type') == 'user']
            name = addr
            if len(names):
                name = names[0]
            if p in http_ports:
                if p == 80:
                    urls.add('http://{}/'.format(name))
                else:
                    urls.add('http://{}:{}/'.format(name, p))
            if p in https_ports:
                if p == 443:
                    urls.add('https://{}/'.format(name))
                else:
                    urls.add('https://{}:{}/'.format(name, p))
    return list(urls)
