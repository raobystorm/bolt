import React from 'react';

export interface Article {
  articleId: number;
  title: string;
  thumbnailPath: string;
  media: string
}

const DailySection = (props: {articles: Article[]}) => {
  return (
    <div>
      {props.articles.map((article) => (
        <p key={article.articleId}>{article.title}</p>
      ))}
    </div>
  );
};

export default DailySection;