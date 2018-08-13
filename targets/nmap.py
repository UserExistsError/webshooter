import xml.etree.ElementTree as ET

def from_xml(xml_file, http_ports, https_ports):
    scan = ET.parse(xml_file).getroot()
    if not scan.tag == 'nmaprun':
        raise ValueError('xml file is not nmap format')
    urls = set()
    for host in scan.findall('./host'):
        open_ports = [int(p.get('portid')) for p in host.findall('./ports/port') if p.find('state').get('state') == 'open']
        for p in open_ports:
            addr = host.findall('./address')[0].get('addr')
            if p in http_ports:
                if p == 80:
                    urls.add('http://{}'.format(addr))
                else:
                    urls.add('http://{}:{}'.format(addr, p))
            if p in https_ports:
                if p == 443:
                    urls.add('https://{}'.format(addr))
                else:
                    urls.add('https://{}:{}'.format(addr, p))
    return list(urls)
