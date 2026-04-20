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


mouseX = 0
mouseY = 0

cookie_clicked = 0
cookieLeft = -700
cookieTop = 0

document.getElementById("cookie").addEventListener("mousedown", function() {
  cookie_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("cookie").addEventListener("mousemove", function() {
      if(cookie_clicked == 0) {
        cookieLeft += event.clientX - mouseX
        cookieTop += event.clientY - mouseY
        document.getElementById("cookie").style.marginLeft = cookieLeft + "px"
        document.getElementById("cookie").style.marginTop = cookieTop + "px"



    

        // typeTop -= event.clientY - mouseY
        // document.getElementById("type").style.marginTop = typeTop + "px"
        imposterTop -= event.clientY - mouseY
        document.getElementById("imposter").style.marginTop = imposterTop + "px"


        mouseX = event.clientX
        mouseY = event.clientY

      }
    })
  
})

document.getElementById("cookie").addEventListener("mouseup", function() {
  cookie_clicked = 1
})




imposter_clicked = 0
imposterLeft = 350
imposterTop = 0

document.getElementById("imposter").addEventListener("mousedown", function() {
  imposter_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("imposter").addEventListener("mousemove", function() {
      if(imposter_clicked == 0) {
        imposterLeft += event.clientX - mouseX
        imposterTop += event.clientY - mouseY
        document.getElementById("imposter").style.marginLeft = imposterLeft + "px"
        document.getElementById("imposter").style.marginTop = imposterTop + "px"

        typeTop -= event.clientY - mouseY
        document.getElementById("type").style.marginTop = typeTop + "px"

        mouseX = event.clientX
        mouseY = event.clientY

      }
    })
  
})

document.getElementById("imposter").addEventListener("mouseup", function() {
  imposter_clicked = 1
})




type_clicked = 0
typeLeft = 100
typeTop = -450

document.getElementById("type").addEventListener("mousedown", function() {
  type_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("type").addEventListener("mousemove", function() {
      if(type_clicked == 0) {
        typeLeft += event.clientX - mouseX
        typeTop += event.clientY - mouseY
        document.getElementById("type").style.marginLeft = typeLeft + "px"
        document.getElementById("type").style.marginTop = typeTop + "px"


        // trainTop -= event.clientY - mouseY
        document.getElementById("train").style.marginTop = trainTop + "px"
        confettiTop -= event.clientY - mouseY
        document.getElementById("confetti").style.marginTop = confettiTop + "px"
        cardTop -= event.clientY - mouseY
        document.getElementById("card").style.marginTop = cardTop + "px"

        mouseX = event.clientX
        mouseY = event.clientY

      }
    })
  
})

document.getElementById("type").addEventListener("mouseup", function() {
  type_clicked = 1
})




card_clicked = 0
cardLeft = -300
cardTop = 0

document.getElementById("card").addEventListener("mousedown", function() {
  card_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("card").addEventListener("mousemove", function() {
      if(card_clicked == 0) {
        cardLeft += event.clientX - mouseX
        cardTop += event.clientY - mouseY
        document.getElementById("card").style.marginLeft = cardLeft + "px"
        document.getElementById("card").style.marginTop = cardTop + "px"



        mouseX = event.clientX
        mouseY = event.clientY

        // cardLeft = event.clientX - 626
        // cardTop = event.clientY - 382
        // document.getElementById("card").style.marginLeft = cardLeft + "px"
        // document.getElementById("card").style.marginTop = cardTop + "px"

      }

      // mouseX = event.clientX
      // mouseY = event.clientY
    })
  
})

document.getElementById("card").addEventListener("mouseup", function() {
  card_clicked = 1
  // console.log(clicked)
})






confetti_clicked = 0
confettiLeft = -400
confettiTop = 80

document.getElementById("confetti").addEventListener("mousedown", function() {
  confetti_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("confetti").addEventListener("mousemove", function() {
      if(confetti_clicked == 0) {
        confettiLeft += event.clientX - mouseX
        confettiTop += event.clientY - mouseY
      


        document.getElementById("confetti").style.marginLeft = confettiLeft + "px"
        document.getElementById("confetti").style.marginTop = confettiTop + "px"


        trainTop -= event.clientY - mouseY
        document.getElementById("train").style.marginTop = trainTop + "px"


        mouseX = event.clientX
        mouseY = event.clientY

      }
    })
  
})

document.getElementById("confetti").addEventListener("mouseup", function() {
  confetti_clicked = 1
})





train_clicked = 0
trainLeft = 100
trainTop = -120

document.getElementById("train").addEventListener("mousedown", function() {
  train_clicked = 0
  mouseX = event.clientX
  mouseY = event.clientY
  
    document.getElementById("train").addEventListener("mousemove", function() {
      if(train_clicked == 0) {
        trainLeft += event.clientX - mouseX
        trainTop += event.clientY - mouseY
        document.getElementById("train").style.marginLeft = trainLeft + "px"
        document.getElementById("train").style.marginTop = trainTop + "px"
        mouseX = event.clientX
        mouseY = event.clientY

      }
    })
  
})

document.getElementById("train").addEventListener("mouseup", function() {
  train_clicked = 1
})
