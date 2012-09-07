$ ->
    client = new Dropbox.Client(
        key: 'a0tctvlgvzakuo9', secret: 'h0aq90h572nd5yp', sandbox: true)
    client.authDriver new Dropbox.Drivers.Redirect(useHash: true)
    new Checkbox client, '#app-ui'
