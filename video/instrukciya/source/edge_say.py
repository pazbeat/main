import sys, os, asyncio, certifi
certifi.where = lambda: '/root/.ccr/ca-bundle.crt'
import edge_tts
async def main(voice, text, out, rate='+0%'):
    c = edge_tts.Communicate(text, voice, rate=rate, proxy=os.environ.get('HTTPS_PROXY'))
    await c.save(out)
if __name__ == '__main__':
    asyncio.run(main(*sys.argv[1:]))
