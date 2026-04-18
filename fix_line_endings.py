content = open(r'E:\Job Search\Project Ideas\Luddy Hackathon\neural-compression-pipeline\service_ocr\entrypoint.sh', 'rb').read().replace(b'\r\n', b'\n')
open(r'E:\Job Search\Project Ideas\Luddy Hackathon\neural-compression-pipeline\service_ocr\entrypoint.sh', 'wb').write(content)
print("Fixed line endings")