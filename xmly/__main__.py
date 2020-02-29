import argparse
from downloader import download

def parse_args():
    parser = argparse.ArgumentParser(
            prog='xmly',
            description='Download audios from ximalaya.com'
            )
    parser.add_argument('url')
    parser.add_argument('-o', dest='output', default='.', help='output folder')
    return parser.parse_args()

def main():
    args = parse_args()
    download(args.url, args.output)

if __name__ == '__main__':
    main()
