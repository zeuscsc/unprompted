class Shortcode():
	def __init__(self,Unprompted):
		self.Unprompted = Unprompted
		self.description = "Applies color correction to a resulting image."
		self.wizard_prepend = Unprompted.Config.syntax.tag_start + "after" + Unprompted.Config.syntax.tag_end + Unprompted.Config.syntax.tag_start_alt + "color_correct"
		self.wizard_append = Unprompted.Config.syntax.tag_end_alt + Unprompted.Config.syntax.tag_start + Unprompted.Config.syntax.tag_close + "after" + Unprompted.Config.syntax.tag_end

	def run_atomic(self, pargs, kwargs, context):
		from PIL import Image
		def autocrop_image(image, border = 0):
			# Get the bounding box
			bbox = image.getbbox()
			# Crop the image to the contents of the bounding box
			image = image.crop(bbox)
			# Determine the width and height of the cropped image
			(width, height) = image.size
			# Add border
			width += border * 2
			height += border * 2
			# Create a new image object for the output image
			cropped_image = Image.new("RGBA", (width, height), (0,0,0,0))
			# Paste the cropped image onto the new image
			cropped_image.paste(image, (border, border))
			# Done!
			return cropped_image

		from blendmodes.blend import blendLayers, BlendType

		color_correct_method = kwargs["method"] if "method" in kwargs else "mkl"
		blend_lum = True if "blend_lum" in pargs else False
		debug = True if "debug" in pargs else False

		try:
			image_to_fix = self.Unprompted.after_processed.images[0].copy()
		except:
			self.Unprompted.log("This must be used inside of an [after] block",context="ERROR")
			return("")
		starting_image = self.Unprompted.p_copy.init_images[0]
		
		orig_image = image_to_fix.copy()
		if self.Unprompted.shortcode_user_vars["image_mask"]:
			mask = self.Unprompted.shortcode_user_vars["image_mask"]
			mask = mask.convert("L")
		else: mask = None

		if "source" in kwargs:
			set_kwargs = kwargs
			set_pargs = pargs
			set_pargs.insert(0,"return_image")
			set_kwargs["txt2mask_init_image"] = starting_image
			set_kwargs["precision"] = "150"
			set_kwargs["padding"] = "0"
			set_kwargs["method"] = "clipseg"
			self.Unprompted.shortcode_user_vars["image_mask"] = None
			source_mask = self.Unprompted.shortcode_objects["txt2mask"].run_block(set_pargs,set_kwargs,None,kwargs["source"])
			source_mask = source_mask.convert("L")
			starting_image.putalpha(source_mask)
			starting_image = autocrop_image(starting_image)

			import cv2
			import numpy
			from sklearn.cluster import KMeans
			np_img = numpy.array(starting_image)
			all_pixels = np_img.reshape(-1, 4)
			#all_pixels.shape
			just_non_alpha = all_pixels[all_pixels[:, 3] == 255]
			#just_non_alpha.shape
			avg_model = KMeans(3)
			reshaped_arr = np_img[:, :, :3].reshape(-1, 3)
			avg_model.fit(np_img[:, :, :3].reshape(-1, 3))	
			KMeans(algorithm='auto', copy_x=True, init='k-means++', max_iter=300,
				n_clusters=3, n_init=10, random_state=None, tol=0.0001, verbose=0)
			print(avg_model.cluster_centers_)
			avg_color = avg_model.cluster_centers_[0]

			if debug: self.Unprompted.log(f"Average color: {avg_color}")

			new_image = Image.new("RGB", starting_image.size, (int(avg_color[0]),int(avg_color[1]),int(avg_color[2])))
			new_image.paste(starting_image, (0, 0), starting_image)  
			if debug: new_image.save("color_correct_alpha_test.png")
			starting_image = new_image.copy()
		

		strength = float(kwargs["strength"]) if "strength" in kwargs else 1.0

		fixed_image = self.Unprompted.color_match(starting_image,image_to_fix,color_correct_method,1).convert("RGBA")

		if blend_lum:
				fixed_image = blendLayers(fixed_image, orig_image, BlendType.LUMINOSITY)

		if strength < 1.0:
			fixed_image.putalpha(int(255 * strength))
		else: self.Unprompted.after_processed.images[0] = fixed_image

		orig_image.paste(fixed_image,(0,0), fixed_image)
		orig_image.resize((self.Unprompted.after_processed.images[0].size[0],self.Unprompted.after_processed.images[0].size[1]))
		self.Unprompted.after_processed.images[0].paste(orig_image,(0,0),mask)

		
		# self.Unprompted.after_processed.images[0] = fixed_image