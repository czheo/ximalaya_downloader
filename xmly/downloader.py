from urllib.parse import urlparse
from multiprocessing import Pool
import os, math, logging, requests
import requests_cache
logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.INFO)

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
LIST_URL_TEMP = 'https://www.ximalaya.com/revision/album/v1/getTracksList?albumId={album_id}&pageNum={page}'
TRACK_URL_TEMP = 'https://www.ximalaya.com/revision/play/v1/audio?id={track_id}&ptype=1'
TRACK_INFO_URL_TEMP = 'https://www.ximalaya.com/revision/track/trackPageInfo?trackId={track_id}'

def download(url, output, process_count = 10):
    url_type, ids = parse_url(url)
    if url_type == 'album':
        requests_cache.install_cache('cache')
        album_id = ids
        logging.info('Download album: ' + album_id)
        folder = create_folder(output)
        tracks = get_tracks(album_id)
        with Pool(process_count) as p:
            res = p.starmap(download_audio, ((track, folder, tracks) for track in tracks))
            logging.info('Total %d/%d succeeded.' % (len([0 for r in res if not r]), len(res)))
            failed = [r for r in res if r]
            if failed:
                logging.info('Failed tracks:')
                for r in failed:
                    print(r)
    elif url_type == 'track':
        track_id = ids
        logging.info('Download track: ' + track_id)
        folder = create_folder(output)
        download_audio({
            'trackId': track_id,
            'title': get_title(track_id),
            'index': 0
            }, folder)

def get_title(track_id):
    url = TRACK_INFO_URL_TEMP.format(track_id = track_id)
    res = requests_get(url)
    return res.json()['data']['trackInfo']['title']

def download_audio(track, folder, tracks = []):
    try:
        url = get_audio_url(track['trackId'])
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
    except:
        logging.error('Track %d/%d failed' % (
            track['index'],
            len(tracks),
            ))
        print(url, track)
        return track

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

def get_audio_url(track_id):
    url = TRACK_URL_TEMP.format(track_id = track_id)
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
        parts = path.strip('/').split('/')
        if len(parts) == 2:
            return ('album', parts[1])
        elif len(parts) == 3:
            if parts[2].startswith('p'):
                return ('album', parts[1])
            else:
                return ('track', parts[2])
        else:
            raise Exception()
    except Exception as e:
        print('invalid url: ' + url)
        raise e
