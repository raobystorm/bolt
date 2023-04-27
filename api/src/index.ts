import express from "express";

const mysql = require('mysql');

const app = express();
const pageSize = 10;

app.get("/timeline/:userId", async (req, res) => {
    const userId = req.params.userId;
    const pageNo = parseInt(req.query.page.toString());
    const offset = pageNo * pageSize;
    const lang = req.query.lang.toString();

    const conn = mysql.createConnection({
        host: "127.0.0.1",
        user: "admin",
        password: "bolt_pass",
        database: "bolt_db"
    });

    conn.connect();

    const query = `SELECT articles.*
        FROM articles
        JOIN user_article ON articles.id = user_article.article_id
        WHERE user_article.user_id = ${userId}
        ORDER BY articles.timestamp DESC
        LIMIT ${pageSize} OFFSET ${offset};`

    conn.query(query, (error, results) => {
        if (error) throw error;
        res.json(results);
    })
});

app.get("/articles/:articleId", async (req, res) => {
    let lang = req.query.lang;

    res.send("article page");
})

app.listen(3000, () => {
    console.log("Server is running on port 3000");
});