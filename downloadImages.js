
const http = require('http')
const https = require('https')
const fs = require('fs')
const path = require('path')

const ordersFile = process.argv[2]
const orders = require(ordersFile)
const saveDir = path.dirname(ordersFile)

function downloadImage(url, destPath) {
    const protocol = url.startsWith('https') ? https : http

    return new Promise((resolve, reject) => {
        protocol.get(url, (response) => {
            if (response.statusCode !== 200) {
                reject(new Error(`Failed to download image. Status code: ${response.statusCode}`))
                return
            }

            const fileStream = fs.createWriteStream(destPath)
            response.pipe(fileStream)

            fileStream.on('finish', () => {
                fileStream.close()
                resolve()
            })

            fileStream.on('error', (error) => {
                fs.unlink(destPath, () => reject(error)) // Delete the file async if there's an error
            })
        }).on('error', (error) => {
            reject(error)
        })
    })
}

const mkdirIfNotExists = (dir) => {
    if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
        fs.mkdirSync(dir, { recursive: true })
    }
}

const main = async () => {
    const deliveriesDir = `${saveDir}/delivery_photos`
    const productsDir = `${saveDir}/product_thumbnails`
    mkdirIfNotExists(deliveriesDir)
    mkdirIfNotExists(productsDir)
    for (let i in orders) {
        if (orders[i].deliveryPhotoUrl) {
            const toDl = `${deliveriesDir}/${orders[i].dateTime.split(' ').join(':').split(':').join('-')}.${path.extname(orders[i].deliveryPhotoUrl)}`
            if (!fs.existsSync(toDl)) {
                downloadImage(
                    orders[i].deliveryPhotoUrl,
                    `${deliveriesDir}/${orders[i].dateTime.split(' ').join(':').split(':').join('-')}.${path.extname(orders[i].deliveryPhotoUrl)}`
                )
            }
        }
        for (let j in orders[i].items) {
            if (orders[i].items[j].thumbnailUrl) {
                const toDl = `${productsDir}/${path.basename(orders[i].items[j].thumbnailUrl)}`
                if (!fs.existsSync(toDl)) {
                    downloadImage(
                        orders[i].items[j].thumbnailUrl,
                        `${productsDir}/${path.basename(orders[i].deliveryPhotoUrl)}`
                    )
                }
            }
        }
    }
}

main().catch(console.error)