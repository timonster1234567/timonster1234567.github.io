let counter = 0
let adder = 1
let per_second = 0

let mouses = 0
let mouseCost = 5

let grandmas = 0
let grandmaCost = 100

let farms = 0
let farmCost = 1100

const total_element = document.getElementById("total")
const mouse_element = document.getElementById("mouse")
const grandma_element = document.getElementById("grandma")
const farm_element = document.getElementById("farm")

const mySound = new Audio('real-button-click.mp3');

main.addEventListener("click", function(){
	counter += adder
	// total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	total_element.innerText = Math.round(counter*10)/10
})

// mouses
mouse.addEventListener("click", function(){
	if(counter>=Math.round(mouseCost)) {
		counter -= Math.round(mouseCost)
		mouses++
		mouseCost = mouseCost*1.5
		createClone("rgb(255, 0, 0)")
	}
	// total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	total_element.innerText = Math.round(counter*10)/10
	mouse_element.innerText = "mouse: $" + Math.round(mouseCost) + " (" + mouses + " mouses)"
	console.log(mouseCost)
})

// grandmas
grandma.addEventListener("click", function(){
	if(counter>=Math.round(grandmaCost)) {
		counter -= Math.round(grandmaCost)
		grandmas++
		grandmaCost = grandmaCost*1.5
		createClone("rgb(50, 205, 100)")
	}
	// total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	total_element.innerText = Math.round(counter*10)/10
	grandma_element.innerText = "grandma: $" + Math.round(grandmaCost) + " (" + grandmas + " grandmas)"
	console.log(grandmaCost)
})

farm.addEventListener("click", function(){
	if(counter>=Math.round(farmCost)) {
		counter -= Math.round(farmCost)
		farms++
		farmCost = farmCost*1.5
		createClone("blue")
	}
	// total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	total_element.innerText = Math.round(counter*10)/10
	farm_element.innerText = "farm: $" + Math.round(farmCost) + " (" + farms + " farms)"
	console.log(farmCost)
})



// adding every second
// let myInterval = setInterval(function() {
//   counter += mouses/10 + grandmas + 10*farms
//   total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
// }, 1000); 



// bounce thing

// marginLeft = getComputedStyle(test_element).marginLeft;
// marginTop = getComputedStyle(test_element).marginTop
// mover_x = 1
// mover_y = 1

// setInterval(function() {
// 	if(parseInt(marginLeft)>(603.2795093-5) || parseInt(marginLeft)<0) {
// 		mover_x = mover_x * (-1)
// 	}

// 	if(parseInt(marginTop)>(498.247902-5) || parseInt(marginTop)<0) {
// 		mover_y = mover_y * (-1)
// 	}

//     marginLeft = (parseInt(marginLeft) + mover_x) + "px"
//     test_element.style.marginLeft = marginLeft

//     marginTop = (parseInt(marginTop) + mover_y) + "px"
//     test_element.style.marginTop = marginTop
// }, 10);



// function startBouncing(element, points) {
//     let marginLeft = parseInt(getComputedStyle(element).marginLeft);
//     let marginTop = parseInt(getComputedStyle(element).marginTop);

//     let mover_x = 2.55;
//     let mover_y = 2.55;

//     setInterval(() => {
//         // Bounce horizontally
//         if (marginLeft > 603.2795094 - 5 || marginLeft < 0) mover_x *= -1 {
//         	total_element.innerText += points;
//         }

//         // Bounce vertically
//         if (marginTop > 489.247902 - 5 || marginTop < 0) mover_y *= -1 {
//         	total_element.innerText += points;
//         }

//         // Move element
//         marginLeft += mover_x;
//         marginTop += mover_y;

//         element.style.marginLeft = marginLeft + "px";
//         element.style.marginTop = marginTop + "px";
//         // element.style.backgroundColor = "rgb(255, 0, 0)"
//     }, 10);
// }

// const test_element = document.getElementById("test");
// startBouncing(test_element);


// function createClone(the_color, points) {

// 	const cloned_test = test_element.cloneNode(true);
// 	cloned_test.id = "test2"
// 	cloned_test.style.position = "absolute"
// 	cloned_test.style.marginLeft = Math.random()*595 + "px"
// 	cloned_test.style.marginTop = Math.random()*480 + "px"

// 	cloned_test.style.backgroundColor = the_color
// 	cloned_test.style.width = 5 + "px"
// 	cloned_test.style.height = 5 + "px"

// 	document.getElementById("box").appendChild(cloned_test);
// 	startBouncing(cloned_test, points);
// }

function startBouncing(element, points) {
    let marginLeft = parseInt(getComputedStyle(element).marginLeft);
    let marginTop = parseInt(getComputedStyle(element).marginTop);

    let mover_x = 2.55;
    let mover_y = 2.55;

    setInterval(() => {
        // Bounce horizontally
        if (marginLeft > 603.2795094 - 5 || marginLeft < 0) {
        	mover_x *= -1;
        	counter += points;
			total_element.innerText = Math.round(counter * 10) / 10;

        	// counter += points
        	console.log(points)
        	if(points > 0) {
        		mySound.pause();
        		mySound.currentTime = 0;
        		mySound.play();
        	}
        }

        // Bounce vertically
        if (marginTop > 489.247902 + 5 || marginTop < 0) {
        	mover_y *= -1;
        	// total_element.innerText += points
        	// total_element.innerText = parseInt(total_element.innerText*10)/10
        	// total_element.innerText += parseInt(points*10)/10
        	counter += points;
			total_element.innerText = Math.round(counter * 10) / 10;

        	console.log(points)
        	if(points > 0) {
        		mySound.pause();
        		mySound.currentTime = 0;
        		mySound.play();
        	}
        } 

        // Move element
        marginLeft += mover_x;
        marginTop += mover_y;

        element.style.marginLeft = marginLeft + "px";
        element.style.marginTop = marginTop + "px";
        // element.style.backgroundColor = "rgb(255, 0, 0)"
    }, 10);
	
}

const test_element = document.getElementById("test");
startBouncing(test_element, 0);


function createClone(the_color) {

	const cloned_test = test_element.cloneNode(true);
	cloned_test.id = "test2"
	cloned_test.style.position = "absolute"
	cloned_test.style.marginLeft = Math.random()*595 + "px"
	cloned_test.style.marginTop = Math.random()*480 + "px"
	console.log(the_color)
	cloned_test.style.backgroundColor = the_color
	cloned_test.style.width = 5 + "px"
	cloned_test.style.height = 5 + "px"

	document.getElementById("box").appendChild(cloned_test);
	if(the_color === "rgb(255, 0, 0)") {
		startBouncing(cloned_test, 0.1);
	} else if (the_color = "rgb(50, 205, 100)") {
		startBouncing(cloned_test, 1);
		console.log("hello")
	} else if (the_color = "blue") {
		startBouncing(cloned_test, 10);
	}
}

marginLeft = getComputedStyle(test_element).marginLeft;
marginTop = getComputedStyle(test_element).marginTop
mover_x = 1
mover_y = 1

setInterval(function() {
	if(parseInt(marginLeft)>(603.2795093-5) || parseInt(marginLeft)<0) {
		mover_x = mover_x * (-1)
	}

	if(parseInt(marginTop)>(498.247902+5) || parseInt(marginTop)<0) {
		mover_y = mover_y * (-1)
	}

    marginLeft = (parseInt(marginLeft) + mover_x) + "px"
    test_element.style.marginLeft = marginLeft

    marginTop = (parseInt(marginTop) + mover_y) + "px"
    test_element.style.marginTop = marginTop
}, 10);


