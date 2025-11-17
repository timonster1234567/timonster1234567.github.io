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

main.addEventListener("click", function(){
	counter += adder
	total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
})

// mouses
mouse.addEventListener("click", function(){
	if(counter>=Math.round(mouseCost)) {
		counter -= Math.round(mouseCost)
		mouses++
		mouseCost = mouseCost*1.5
	}
	total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	mouse_element.innerText = "mouse: $" + Math.round(mouseCost) + " (" + mouses + " mouses)"
	console.log(mouseCost)
})

// grandmas
grandma.addEventListener("click", function(){
	if(counter>=Math.round(grandmaCost)) {
		counter -= Math.round(grandmaCost)
		grandmas++
		grandmaCost = grandmaCost*1.5
	}
	total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	grandma_element.innerText = "grandma: $" + Math.round(grandmaCost) + " (" + gradmas + " grandmas)"
	console.log(grandmaCost)
})

farm.addEventListener("click", function(){
	if(counter>=Math.round(farmCost)) {
		counter -= Math.round(farmCost)
		farms++
		farmCost = farmCost*1.5
	}
	total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
	farm_element.innerText = "farm: $" + Math.round(farmCost) + " (" + farms + " farms)"
	console.log(farmCost)
})




let myInterval = setInterval(function() {
  counter += mouses/10 + grandmas + 10*farms
  total_element.innerText = Math.round(counter*10)/10 + " - " + (mouses/10 + grandmas + 10*farms)
}, 1000); 



// bounce thing
const test_element = document.getElementById("test");

setInterval(function() {
    marginLeft = getComputedStyle(test_element).marginLeft;
    marginLeft = (parseInt(marginLeft) + 1) + "px"
    console.log(marginLeft);
}, 100);
