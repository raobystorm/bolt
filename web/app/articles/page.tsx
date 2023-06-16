"use client";

import React, { useState, useEffect } from 'react';
import DailySection, { Article } from '../../components/DailySection/DailySection';

const Timeline = () => {
  const [items, setItems] = useState(new Map<string, Article[]>);
  const [page, setPage] = useState(0);

  // Function to fetch data (can be your API call)
  const fetchData = async () => {
    const res = await fetch(`http://localhost:3000/timeline/1?page=${page}&lang=zh-CN`);
    const newItems = await res.json();
  
    setItems(prevState => {
      Object.keys(newItems).forEach(key => {
        const articles: Article[] = newItems[key];
        if(!prevState.has(key)) {
          prevState.set(key, []);
        }
        prevState.set(key, [...prevState.get(key)!, ...articles]);
      })
      return prevState;
    })
  };

  // Fetch data initially when component mounts
  useEffect(() => {
    fetchData();
  }, []);

  // Fetch additional data when page increases
  useEffect(() => {
    if (page > 1) {
      fetchData();
    }
  }, [page]);

  // Function to handle scroll event
  const handleScroll = (e: any) => {
    const bottom = e.target.scrollHeight - e.target.scrollTop === e.target.clientHeight;
    if (bottom) {
      setPage(prevPage => prevPage + 1);
    }
  };

  // Adding event listener when component mounts
  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <div>
      {[...items].map(([key, value]) => (
        <div key={key}>
          <h1>{key}</h1>
        </div>
      ))}
    </div>
  );
};

export default Timeline;