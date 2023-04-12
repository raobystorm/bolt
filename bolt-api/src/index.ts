import express from "express";

const app = express();

app.get("/timeline/:userId", async (req, res) => {
    let page = req.query.page;
    let lang = req.query.lang;

    res.send("Time line");
});

app.get("/articles/:articleId",async (req, res) => {
    let lang = req.query.lang;

    res.send("article page");
})

app.listen(3000, () => {
    console.log("Server is running on port 3000");
});