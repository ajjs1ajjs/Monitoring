import asyncio

import httpx


async def run():
    async with httpx.AsyncClient() as client:
        r = await client.post('http://127.0.0.1:10000/api/v1/auth/login', json={'username':'admin','password':'291263'})
        token = r.json()['access_token']
        r2 = await client.post(
            'http://127.0.0.1:10000/api/v1/servers',
            headers={'Authorization': f'Bearer {token}'},
            json={'name':'Test Node', 'host':'127.0.0.1', 'os_type':'linux', 'agent_port':10000, 'enabled':True}
        )
        print(r2.status_code, r2.text)

asyncio.run(run())
