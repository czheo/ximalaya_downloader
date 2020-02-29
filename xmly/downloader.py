from urllib.parse import urlparse
import os, math, logging, requests
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
LIST_URL_TEMP = 'https://www.ximalaya.com/revision/album/v1/getTracksList?albumId={album_id}&pageNum={page}'
TRACK_URL_TEMP = 'https://www.ximalaya.com/revision/play/v1/audio?id={track_id}&ptype=1'

def download(url, output):
    album_id = parse_url(url)
    folder = create_folder(output)
    tracks = get_tracks(album_id)
    for track in tracks:
        download_audio(track, folder, tracks)

def download_audio(track, folder, tracks):
    url = get_audio_url(track, folder)
    ext = url.rsplit('.')[-1]
    file_path = os.path.join(folder, track['title'].strip() + '.' + ext)
    logging.info('Downloading: %s' % url)
    size = download_file(url, file_path)
    logging.info('Track %d/%d, %s: %s' % (
        track['index'],
        len(tracks),
        sizeof_fmt(size),
        file_path,
        ))

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'G', suffix)

def download_file(url, path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
            return os.fstat(f.fileno()).st_size

def get_audio_url(track, folder):
    url = TRACK_URL_TEMP.format(track_id = track['trackId'])
    res = requests_get(url).json()
    src = res['data']['src']
    return src

def requests_get(url):
    headers = {'User-Agent': UA}
    return requests.get(url, headers=headers)

def get_tracks(album_id):
    tracks = []
    p1 = get_lists(album_id, 1)
    total = p1['data']['trackTotalCount']
    page_size = p1['data']['pageSize']
    total_pages = math.ceil(total / page_size)
    tracks += p1['data']['tracks']
    for i in range(2, total_pages + 1):
        res = get_lists(album_id, i)
        tracks += res['data']['tracks']
    logging.info('Total tracks to fetch: %d' % total)
    logging.info('Total tracks fetched: %d' % len(tracks))
    return tracks

def get_lists(album_id, page):
    url = LIST_URL_TEMP.format(album_id = album_id, page = page)
    res = requests_get(url).json()
    logging.info('Fetched page %d with %d tracks: %s' % (page, len(res['data']['tracks']), url))
    return res

def create_folder(output):
    if os.path.isdir(output):
        return output
    elif not os.path.exists(output):
        os.mkdir(output)
        logging.info('New folder created: ' + output)
        return output
    else:
        raise Exception('invalid folder: ' + output)

def parse_url(url):
    try:
        path = urlparse(url).path
        parts = path.split('/')
        return parts[2]
    except Exception as e:
        print('invalid url: ' + url)
        raise e
