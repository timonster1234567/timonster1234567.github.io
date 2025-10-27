document.addEventListener('DOMContentLoaded', function() {
  const scrollToProjectsButton = document.getElementById('scrollToProjectsButton');
  const page1 = document.getElementById('page1');

  scrollToProjectsButton.addEventListener('click', function() {
    page1.scrollIntoView({
      behavior: 'smooth', // Optional: for smooth scrolling
      block: 'start' // Optional: aligns the top of the element with the top of the scroll area
    });
  });
});

document.addEventListener('DOMContentLoaded', function() {
  const scrollToJournalButton = document.getElementById('scrollToJournalButton');
  const page2 = document.getElementById('page2');

  scrollToJournalButton.addEventListener('click', function() {
    page2.scrollIntoView({
      behavior: 'smooth', // Optional: for smooth scrolling
      block: 'start' // Optional: aligns the top of the element with the top of the scroll area
    });
  });
});

document.addEventListener('DOMContentLoaded', function() {
  const scrollToAboutMeButton = document.getElementById('scrollToAboutMeButton');
  const page3 = document.getElementById('page3');

  scrollToAboutMeButton.addEventListener('click', function() {
    page3.scrollIntoView({
      behavior: 'smooth', // Optional: for smooth scrolling
      block: 'start' // Optional: aligns the top of the element with the top of the scroll area
    });
  });
});