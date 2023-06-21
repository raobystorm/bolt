import Image from 'next/image';
import React, { useState } from 'react';
import InfiniteScroll from 'react-infinite-scroll-component';

export interface Article {
  articleId: number;
  title: string;
  publishDate: string;
  summary: string;
  thumbnailPath: string;
  media: string;
}

const Timeline = ({ articles }: { articles: Article[] }) => {
  const [items, setItems] = useState<Article[]>(articles);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);

  // Function to fetch data (can be your API call)
  const getMoreArticles = async () => {
    const res = await fetch(
      `http://bolt_devcontainer:3000/timeline/1?page=${page}&lang=zh-CN`,
    );
    const newItems: { articles: Article[] } = await res.json();
    setItems((prevState) => {
      return [...prevState, ...newItems.articles];
    });
  };

  return (
    <InfiniteScroll
      dataLength={items.length}
      next={getMoreArticles}
      hasMore={hasMore}
      loader={<h3> Loading... </h3>}
      endMessage={<h4> No more articles </h4>}
    >
      {items.map((article) => (
        <div className='flex flex-row' key={article.articleId}>
          <Image
            src={article.thumbnailPath}
            alt={article.title}
            width={80}
            height={60}
          />
          <div>{article.title}</div>
        </div>
      ))}
    </InfiniteScroll>
  );
};

export default Timeline;
