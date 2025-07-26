const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

const uploadDir = path.join(__dirname, 'uploads');
const dbFile = path.join(__dirname, 'files.json');

if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir);
}

function readDB() {
    try {
        return JSON.parse(fs.readFileSync(dbFile));
    } catch (e) {
        return [];
    }
}

function writeDB(data) {
    fs.writeFileSync(dbFile, JSON.stringify(data, null, 2));
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, uploadDir),
    filename: (req, file, cb) => cb(null, Date.now() + '_' + file.originalname)
});

const upload = multer({ storage });

app.use(express.json());
app.use(express.static(__dirname));

app.post('/api/upload', upload.single('file'), (req, res) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
    const files = readDB();
    files.push({
        id,
        name: req.file.originalname,
        path: req.file.filename,
        size: req.file.size,
        type: req.file.mimetype,
        privacy: 'private',
        downloads: 0
    });
    writeDB(files);
    res.json({ id });
});

app.get('/api/files', (req, res) => {
    const files = readDB();
    res.json(files);
});

app.get('/api/files/:id', (req, res) => {
    const files = readDB();
    const file = files.find(f => f.id === req.params.id);
    if (!file) return res.status(404).send('Not found');
    res.json(file);
});

app.get('/files/:id', (req, res) => {
    const files = readDB();
    const file = files.find(f => f.id === req.params.id);
    if (!file) return res.status(404).send('Not found');
    file.downloads++;
    writeDB(files);
    res.sendFile(path.join(uploadDir, file.path));
});

app.patch('/api/files/:id', (req, res) => {
    const files = readDB();
    const file = files.find(f => f.id === req.params.id);
    if (!file) return res.status(404).send('Not found');
    if (req.body.privacy) file.privacy = req.body.privacy;
    writeDB(files);
    res.json(file);
});

app.delete('/api/files/:id', (req, res) => {
    let files = readDB();
    const index = files.findIndex(f => f.id === req.params.id);
    if (index === -1) return res.status(404).send('Not found');
    const [file] = files.splice(index, 1);
    fs.unlink(path.join(uploadDir, file.path), () => {});
    writeDB(files);
    res.sendStatus(204);
});

app.listen(PORT, () => console.log(`Server started on port ${PORT}`));

